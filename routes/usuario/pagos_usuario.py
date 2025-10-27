from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session, jsonify, send_from_directory
from models.baseDatos import db, Reserva, nuevaHabitacion, TicketHospedaje, ReservaDatosHospedaje, Usuario
from utils.mailer import send_email
import os
import requests
import hmac
import hashlib
import io

mercadopago = None  # import dinámico cuando se necesite

pagos_usuario_bp = Blueprint('pagos_usuario', __name__)


def _current_user_id():
    return session.get('user', {}).get('id')


def _payment_provider() -> str:
    return (os.getenv('PAYMENT_PROVIDER', 'WOMPI') or 'WOMPI').strip().upper()


@pagos_usuario_bp.route('/pago/checkout/<int:reserva_id>')
def checkout_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    # Seguridad básica: la reserva debe pertenecer al usuario actual
    uid = _current_user_id()
    if not uid or reserva.usuario_id != uid:
        flash('No autorizado para pagar esta reserva', 'danger')
        return redirect(url_for('registro.login'))

    # Decidir proveedor
    provider = _payment_provider()
    reference = f"RES-{reserva.id}"
    habitacion = nuevaHabitacion.query.get(reserva.habitacion_id)

    if provider == 'MP':
        # Mercado Pago Checkout Pro (redirect a init_point)
        if mercadopago is None:
            try:
                import mercadopago as _mp
                globals()['mercadopago'] = _mp
            except Exception:
                flash('Mercado Pago no está instalado en el servidor. Contacta al administrador.', 'danger')
                return redirect(url_for('perfil_usuario.perfil'))
        access_token = os.getenv('MP_ACCESS_TOKEN')
        if not access_token:
            flash('Falta configurar MP_ACCESS_TOKEN para Mercado Pago.', 'danger')
            return redirect(url_for('perfil_usuario.perfil'))
        sdk = mercadopago.SDK(access_token)
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        success_url = url_for('pagos_usuario.mp_retorno', _external=True, _scheme=scheme, status='success', ref=reference)
        failure_url = url_for('pagos_usuario.mp_retorno', _external=True, _scheme=scheme, status='failure', ref=reference)
        pending_url = url_for('pagos_usuario.mp_retorno', _external=True, _scheme=scheme, status='pending', ref=reference)
        notif_url = url_for('pagos_usuario.mp_webhook', _external=True, _scheme=scheme)

        item_title = f"Habitación {habitacion.nombre if habitacion else reserva.habitacion_id} ({reference})"
        preference_data = {
            "items": [
                {
                    "title": item_title,
                    "quantity": 1,
                    "currency_id": "COP",
                    "unit_price": float(reserva.total or 0)
                }
            ],
            "external_reference": reference,
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url
            },
            "auto_return": "approved",
            "notification_url": notif_url
        }
        try:
            pref_resp = sdk.preference().create(preference_data)
            init = pref_resp.get('response', {}).get('init_point') or pref_resp.get('response', {}).get('sandbox_init_point')
            if not init:
                current_app.logger.warning('No se obtuvo init_point de Mercado Pago: %s', pref_resp)
                flash('No se pudo iniciar el pago con Mercado Pago.', 'danger')
                return redirect(url_for('perfil_usuario.perfil'))
            return redirect(init)
        except Exception as e:
            current_app.logger.exception('Error creando preferencia de Mercado Pago: %s', e)
            flash('Error iniciando pago con Mercado Pago.', 'danger')
            return redirect(url_for('perfil_usuario.perfil'))

    if provider == 'EPAYCO':
        # EPAYCO Checkout (script) con response y confirmation URLs
        pub = os.getenv('EPAYCO_PUBLIC_KEY')
        p_key = os.getenv('EPAYCO_PRIVATE_KEY')  # Para firma de verificación (no expone en front)
        cust = os.getenv('EPAYCO_P_CUST_ID_CLIENTE')
        if not pub or not p_key or not cust:
            flash('Falta configurar EPAYCO_PUBLIC_KEY, EPAYCO_PRIVATE_KEY o EPAYCO_P_CUST_ID_CLIENTE.', 'danger')
            return redirect(url_for('perfil_usuario.perfil'))

        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        response_url = url_for('pagos_usuario.epayco_retorno', _external=True, _scheme=scheme)
        confirm_url = url_for('pagos_usuario.epayco_confirmacion', _external=True, _scheme=scheme)
        amount = float(reserva.total or 0)
        currency = 'cop'
        country = 'co'
        test = 'true' if str(os.getenv('EPAYCO_TEST', '1')).lower() in ('1','true','yes','on') else 'false'
        invoice = str(reserva.id)
        reference = f"RES-{reserva.id}"
        title = f"Habitación {habitacion.nombre if habitacion else reserva.habitacion_id}"
        description = f"Reserva {reference}"

        return render_template(
            'usuario/checkout_epayco.html',
            reserva=reserva,
            habitacion=habitacion,
            epayco_public_key=pub,
            amount=amount,
            currency=currency,
            country=country,
            test=test,
            invoice=invoice,
            reference=reference,
            title=title,
            description=description,
            response_url=response_url,
            confirm_url=confirm_url,
        )

    # WOMPI (por defecto)
    public_key = os.getenv('WOMPI_PUBLIC_KEY', 'pub_test_ATgfa6zjR4rV4i2O1RrE8Gxx')  # Placeholder test key
    scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
    redirect_url = url_for('pagos_usuario.wompi_retorno', _external=True, _scheme=scheme)
    amount_in_cents = int((reserva.total or 0) * 100)

    return render_template(
        'usuario/checkout_wompi.html',
        reserva=reserva,
        habitacion=habitacion,
        wompi_public_key=public_key,
        amount_in_cents=amount_in_cents,
        reference=reference,
        redirect_url=redirect_url,
        currency='COP',
        country='CO'
    )


@pagos_usuario_bp.route('/pago/wompi/retorno')
def wompi_retorno():
    # Validación con API de Wompi
    tx_id = request.args.get('id')
    ref = request.args.get('reference')
    status_q = request.args.get('status') or request.args.get('statusMessage')

    if not ref or not ref.startswith('RES-'):
        flash('Referencia de pago inválida', 'danger')
        return redirect(url_for('main.home_usuario'))

    try:
        rid = int(ref.split('-')[1])
    except Exception:
        flash('Referencia de pago inválida', 'danger')
        return redirect(url_for('main.home_usuario'))

    reserva = Reserva.query.get(rid)
    if not reserva:
        flash('Reserva no encontrada', 'danger')
        return redirect(url_for('main.home_usuario'))

    status_final = (status_q or '').upper()

    # Intentar verificar con Wompi si tenemos id de transacción
    if tx_id:
        base = _wompi_base_url()
        try:
            resp = requests.get(f"{base}/v1/transactions/{tx_id}", timeout=10)
            if resp.ok:
                data = resp.json() or {}
                status_final = (data.get('data', {}).get('status') or status_final or '').upper()
                ref_api = data.get('data', {}).get('reference')
                # Si la referencia de API no coincide, no arriesgar estado
                if ref_api and ref_api != ref:
                    current_app.logger.warning('Referencia Wompi no coincide. ref=%s api=%s', ref, ref_api)
            else:
                current_app.logger.warning('No se pudo verificar transacción Wompi %s: %s', tx_id, resp.text)
        except Exception as e:
            current_app.logger.exception('Error verificando Wompi: %s', e)

    _apply_status_to_reserva(reserva, status_final)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    if status_final == 'APPROVED':
        flash('Pago aprobado. ¡Gracias!', 'success')
    elif status_final in ('DECLINED', 'ERROR', 'VOIDED'):  # distintos estados negativos
        flash('El pago no fue aprobado. Puedes intentarlo nuevamente.', 'danger')
    else:
        flash('Pago en proceso. Te informaremos cuando sea confirmado.', 'info')

    return redirect(url_for('perfil_usuario.perfil'))


# ---------------- MERCADO PAGO ---------------- #

@pagos_usuario_bp.route('/pago/mp/retorno')
def mp_retorno():
    ref = request.args.get('ref') or ''
    status = (request.args.get('status') or '').lower()
    if not ref.startswith('RES-'):
        flash('Referencia inválida', 'danger')
        return redirect(url_for('main.home_usuario'))
    try:
        rid = int(ref.split('-')[1])
    except Exception:
        flash('Referencia inválida', 'danger')
        return redirect(url_for('main.home_usuario'))

    reserva = Reserva.query.get(rid)
    if not reserva:
        flash('Reserva no encontrada', 'danger')
        return redirect(url_for('main.home_usuario'))

    # Mapear estados
    if status == 'success':
        mp_status = 'APPROVED'
    elif status == 'failure':
        mp_status = 'REJECTED'
    else:
        mp_status = 'PENDING'

    _apply_status_to_reserva(reserva, mp_status)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    if mp_status == 'APPROVED':
        flash('Pago aprobado (Mercado Pago).', 'success')
    elif mp_status == 'REJECTED':
        flash('El pago fue rechazado (Mercado Pago).', 'danger')
    else:
        flash('Pago en proceso (Mercado Pago).', 'info')
    return redirect(url_for('perfil_usuario.perfil'))


@pagos_usuario_bp.route('/pago/mp/webhook', methods=['POST'])
def mp_webhook():
    # Nota: Validaciones de firma pueden añadirse (x-signature). Aquí priorizamos flujo básico.
    payload = request.get_json(silent=True) or {}
    topic = (payload.get('type') or payload.get('topic') or '').lower()
    data = payload.get('data') or {}
    payment_id = data.get('id') or data.get('payment_id')

    status = None
    ref = None
    if mercadopago and payment_id:
        try:
            access_token = os.getenv('MP_ACCESS_TOKEN')
            sdk = mercadopago.SDK(access_token)
            p = sdk.payment().get(payment_id)
            pr = p.get('response', {})
            status = (pr.get('status') or '').upper()
            ref = pr.get('external_reference') or ''
        except Exception as e:
            current_app.logger.exception('Error consultando pago MP: %s', e)

    if not ref or not ref.startswith('RES-'):
        return jsonify({'ok': True})

    try:
        rid = int(ref.split('-')[1])
    except Exception:
        return jsonify({'ok': True})

    reserva = Reserva.query.get(rid)
    if not reserva:
        return jsonify({'ok': True})

    # Convertir estados de MP a internos
    map_status = {
        'APPROVED': 'APPROVED',
        'REJECTED': 'REJECTED',
        'PENDING': 'PENDING',
        'IN_PROCESS': 'PENDING',
        'IN_MEDIATION': 'PENDING'
    }
    st = map_status.get(status or 'PENDING', 'PENDING')
    _apply_status_to_reserva(reserva, st)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error guardando estado reserva MP: %s', e)
        return jsonify({'ok': False}), 500

    return jsonify({'ok': True})


@pagos_usuario_bp.route('/pago/wompi/webhook', methods=['POST'])
def wompi_webhook():
    # Valida firma HMAC para garantizar que el evento proviene de Wompi
    secret = os.getenv('WOMPI_EVENTS_SECRET') or os.getenv('WOMPI_WEBHOOK_SECRET') or ''
    sig = request.headers.get('X-Event-Signature', '')
    if not secret or not sig:
        return jsonify({'ok': False, 'error': 'missing_signature'}), 400

    try:
        expected = 'sha256=' + hmac.new(secret.encode('utf-8'), request.data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            current_app.logger.warning('Firma de webhook inválida. Expected %s got %s', expected, sig)
            return jsonify({'ok': False, 'error': 'invalid_signature'}), 400
    except Exception as e:
        current_app.logger.exception('Error validando firma: %s', e)
        return jsonify({'ok': False, 'error': 'signature_error'}), 400

    payload = request.get_json(silent=True) or {}
    event = payload.get('event') or payload.get('eventName') or ''
    data = payload.get('data') or {}
    tx = data.get('transaction') or {}
    status = (tx.get('status') or '').upper()
    ref = tx.get('reference') or ''

    if not ref.startswith('RES-'):
        return jsonify({'ok': True})  # ignorar eventos que no son de reservas

    try:
        rid = int(ref.split('-')[1])
    except Exception:
        return jsonify({'ok': True})

    reserva = Reserva.query.get(rid)
    if not reserva:
        return jsonify({'ok': True})

    _apply_status_to_reserva(reserva, status)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error guardando estado reserva: %s', e)
        return jsonify({'ok': False}), 500

    return jsonify({'ok': True})


def _wompi_base_url():
    # Determina sandbox o producción según la llave pública
    pub = os.getenv('WOMPI_PUBLIC_KEY', '')
    if pub.startswith('pub_test'):
        return 'https://sandbox.wompi.co'
    return 'https://production.wompi.co'


# ----------------- HOSPEDAJE TICKET HELPERS ----------------- #
def _gen_ht_ticket_number():
    from datetime import datetime as _dt
    return _dt.utcnow().strftime('HT%Y%m%d%H%M%S')


def _ensure_ticket_for_reserva(reserva: Reserva):
    """Crea un TicketHospedaje y su PDF si la reserva está completada y aún no tiene ticket."""
    if not reserva or reserva.estado != 'Completada':
        return None
    t = TicketHospedaje.query.filter_by(reserva_id=reserva.id).first()
    if t:
        return t
    user = Usuario.query.get(reserva.usuario_id)
    hab = nuevaHabitacion.query.get(reserva.habitacion_id)
    datos = ReservaDatosHospedaje.query.filter_by(reserva_id=reserva.id).first()

    t = TicketHospedaje(
        ticket_numero=_gen_ht_ticket_number(),
        reserva_id=reserva.id,
        usuario_id=reserva.usuario_id,
        habitacion_id=reserva.habitacion_id,
        habitacion_numero=str(hab.numero) if hab and hab.numero is not None else None,
        nombre1=(datos.nombre1 if datos else (user.usuario if user else '')),
        tipo_doc1=(datos.tipo_doc1 if datos else ''),
        num_doc1=(datos.num_doc1 if datos else ''),
        telefono1=(datos.telefono1 if datos else (user.telefono if user else None)),
        correo1=(datos.correo1 if datos else (user.correo if user else None)),
        procedencia1=(datos.procedencia1 if datos else None),
        nombre2=(datos.nombre2 if datos else None),
        tipo_doc2=(datos.tipo_doc2 if datos else None),
        num_doc2=(datos.num_doc2 if datos else None),
        telefono2=(datos.telefono2 if datos else None),
        correo2=(datos.correo2 if datos else None),
        procedencia2=(datos.procedencia2 if datos else None),
        check_in=reserva.check_in,
        check_out=reserva.check_out or reserva.check_in,
        total=float(reserva.total or 0),
    )
    db.session.add(t)
    db.session.flush()

    # Construir PDF
    try:
        pdf_bytes = _build_hospedaje_ticket_pdf(t, hab)
        tickets_dir = os.path.join(current_app.instance_path, 'uploads', 'tickets_hospedaje')
        os.makedirs(tickets_dir, exist_ok=True)
        path = os.path.join(tickets_dir, f"{t.ticket_numero}.pdf")
        with open(path, 'wb') as f:
            f.write(pdf_bytes.getvalue())
        t.file_ticket = f"uploads/tickets_hospedaje/{t.ticket_numero}.pdf"
        # Intentar enviar por correo al usuario
        try:
            if user and user.correo:
                subject = f"Tu ticket de reserva #{reserva.id}"
                body = (
                    f"<p>Hola {user.usuario},</p>"
                    f"<p>Adjuntamos tu ticket de hospedaje para la reserva #{reserva.id}.</p>"
                    f"<p>Check-in: {t.check_in} · Check-out: {t.check_out}</p>"
                    f"<p>Gracias por tu reserva.</p>"
                )
                attach_name = f"{t.ticket_numero}.pdf"
                send_email(user.correo, subject, body, [(attach_name, pdf_bytes.getvalue())])
        except Exception:
            pass
    except Exception as e:
        try:
            current_app.logger.warning('No se pudo generar/guardar el PDF de ticket: %s', e)
        except Exception:
            pass

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return t


def _build_hospedaje_ticket_pdf(ticket: TicketHospedaje, habitacion: nuevaHabitacion):
    buf = io.BytesIO()
    # Importar reportlab de forma perezosa
    try:
        from reportlab.lib.pagesizes import A4 as _A4
        from reportlab.pdfgen import canvas as _canvas
        c = _canvas.Canvas(buf, pagesize=_A4)
        width, height = _A4
    except Exception:
        buf.write((f"Ticket {ticket.ticket_numero}\n").encode('utf-8'))
        buf.seek(0)
        return buf
    y = height - 50
    c.setFont('Helvetica-Bold', 16)
    c.drawString(40, y, 'Reserva Hospedaje - Ticket')
    y -= 25
    c.setFont('Helvetica', 11)
    c.drawString(40, y, f"Ticket: {ticket.ticket_numero}")
    y -= 18
    c.drawString(40, y, f"Habitación: {habitacion.nombre if habitacion else ticket.habitacion_id}  (# {ticket.habitacion_numero or '-'})")
    y -= 18
    c.drawString(40, y, f"Check-in: {ticket.check_in.strftime('%Y-%m-%d')}  ·  Check-out: {ticket.check_out.strftime('%Y-%m-%d')}")
    y -= 18
    try:
        noches = max(1, (ticket.check_out - ticket.check_in).days)
    except Exception:
        noches = 1
    c.drawString(40, y, f"Noches: {noches}")
    y -= 28
    c.setFont('Helvetica-Bold', 12)
    c.drawString(40, y, 'Huésped titular:')
    y -= 18
    c.setFont('Helvetica', 11)
    c.drawString(50, y, f"Nombre: {ticket.nombre1}")
    y -= 16
    c.drawString(50, y, f"Documento: {ticket.tipo_doc1 or ''} {ticket.num_doc1 or ''}")
    y -= 16
    c.drawString(50, y, f"Teléfono: {ticket.telefono1 or '-'} · Correo: {ticket.correo1 or '-'}")
    y -= 16
    c.drawString(50, y, f"Procedencia: {ticket.procedencia1 or '-'}")
    if ticket.nombre2:
        y -= 24
        c.setFont('Helvetica-Bold', 12)
        c.drawString(40, y, 'Acompañante:')
        y -= 18
        c.setFont('Helvetica', 11)
        c.drawString(50, y, f"Nombre: {ticket.nombre2}")
        y -= 16
        doc2 = ((ticket.tipo_doc2 or '') + ' ' + (ticket.num_doc2 or '')).strip()
        if doc2:
            c.drawString(50, y, f"Documento: {doc2}")
            y -= 16
        if ticket.telefono2 or ticket.correo2:
            c.drawString(50, y, f"Teléfono: {ticket.telefono2 or '-'} · Correo: {ticket.correo2 or '-'}")
            y -= 16
        if ticket.procedencia2:
            c.drawString(50, y, f"Procedencia: {ticket.procedencia2}")
            y -= 16
    y -= 10
    c.setFont('Helvetica-Bold', 12)
    c.drawString(40, y, f"Total pagado: ${ticket.total:,.0f} COP")
    y -= 24
    c.setFont('Helvetica-Oblique', 10)
    c.drawString(40, y, 'Presenta este ticket en recepción para validar tu reserva.')
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


@pagos_usuario_bp.route('/hospedaje/ticket/<int:reserva_id>')
def descargar_ticket_hospedaje(reserva_id: int):
    reserva = Reserva.query.get_or_404(reserva_id)
    user = session.get('user') or {}
    is_admin = (user.get('rol') == 'admin')
    if not is_admin and user.get('id') != reserva.usuario_id and user.get('idUsuario') != reserva.usuario_id:
        flash('No autorizado', 'danger')
        return redirect(url_for('registro.login'))
    t = TicketHospedaje.query.filter_by(reserva_id=reserva.id).first()
    if not t and reserva.estado == 'Completada':
        t = _ensure_ticket_for_reserva(reserva)
    if not t or not t.file_ticket:
        flash('El ticket aún no está disponible.', 'warning')
        return redirect(url_for('perfil_usuario.perfil'))
    rel = t.file_ticket.replace('\\', '/').lstrip('/')
    if rel.startswith('uploads/'):
        base = current_app.instance_path
        subdir, fname = os.path.split(rel)
        return send_from_directory(os.path.join(base, subdir), fname, as_attachment=True)
    base = os.path.dirname(t.file_ticket)
    fname = os.path.basename(t.file_ticket)
    return send_from_directory(base, fname, as_attachment=True)


def _apply_status_to_reserva(reserva: Reserva, wompi_status: str):
    st = (wompi_status or '').upper()
    if st == 'APPROVED':
        # Mantener bloqueadas las fechas: 'Completada' confirma ocupación
        reserva.estado = 'Completada'
        # Generar ticket de hospedaje si no existe
        try:
            _ensure_ticket_for_reserva(reserva)
        except Exception as e:
            try:
                current_app.logger.exception('Error generando ticket de hospedaje: %s', e)
            except Exception:
                pass
    elif st in ('DECLINED', 'ERROR', 'VOIDED'):  # cancelada/declinada
        # Liberar fechas: 'Cancelada' libera disponibilidad para ese rango
        reserva.estado = 'Cancelada'
    else:
        reserva.estado = 'Activa'


# ----------------- EPAYCO HANDLERS ----------------- #

def _epayco_verify_signature(data: dict) -> bool:
    """Verifica la firma de ePayco para confirmaciones/retornos.
    Firma: md5(p_cust_id_cliente^p_key^x_ref_payco^x_transaction_id^x_amount^x_currency_code)
    """
    try:
        import hashlib
        cust = os.getenv('EPAYCO_P_CUST_ID_CLIENTE', '')
        pkey = os.getenv('EPAYCO_PRIVATE_KEY', '')
        ref_payco = str(data.get('x_ref_payco', ''))
        tx_id = str(data.get('x_transaction_id', ''))
        amount = str(data.get('x_amount', ''))
        curr = str(data.get('x_currency_code', ''))
        signature = (data.get('x_signature') or '').lower()
        comp = f"{cust}^{pkey}^{ref_payco}^{tx_id}^{amount}^{curr}"
        md5h = hashlib.md5(comp.encode('utf-8')).hexdigest().lower()
        return md5h == signature and all([cust, pkey, ref_payco, tx_id, amount, curr])
    except Exception:
        return False


def _epayco_extract_reserva_id(data: dict) -> int | None:
    # Intentar por x_id_invoice (string del invoice) o x_extra1 (nuestra reference), o ref simple
    inv = data.get('x_id_invoice') or data.get('x_invoice_id') or data.get('invoice') or data.get('p_id_invoice')
    if inv:
        try:
            return int(str(inv))
        except Exception:
            pass
    ref = data.get('x_extra1') or data.get('external_reference') or data.get('ref') or ''
    if ref and str(ref).startswith('RES-'):
        try:
            return int(str(ref).split('-')[1])
        except Exception:
            return None
    return None


def _epayco_map_status(text: str) -> str:
    t = (text or '').strip().lower()
    if t in ('aceptada', 'approved', 'success'):  # según idioma
        return 'APPROVED'
    if t in ('rechazada', 'rejected', 'failure', 'fallida'):
        return 'DECLINED'
    return 'PENDING'


@pagos_usuario_bp.route('/pago/epayco/retorno')
def epayco_retorno():
    # Retorno del navegador (GET)
    data = request.args.to_dict(flat=True)
    rid = _epayco_extract_reserva_id(data)
    if not rid:
        flash('Referencia de pago inválida (ePayco)', 'danger')
        return redirect(url_for('main.home_usuario'))

    reserva = Reserva.query.get(rid)
    if not reserva:
        flash('Reserva no encontrada', 'danger')
        return redirect(url_for('main.home_usuario'))

    # Intentar verificar firma si están los campos
    if not _epayco_verify_signature(data):
        current_app.logger.warning('Firma ePayco inválida en retorno: %s', data)
        # No abortamos; puede ser retorno sin firma. Dejar estado como esté.

    status = _epayco_map_status(data.get('x_transaction_state') or data.get('status'))
    _apply_status_to_reserva(reserva, status)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    if status == 'APPROVED':
        flash('Pago aprobado (ePayco).', 'success')
    elif status == 'DECLINED':
        flash('El pago fue rechazado (ePayco).', 'danger')
    else:
        flash('Pago en proceso (ePayco).', 'info')
    return redirect(url_for('perfil_usuario.perfil'))


@pagos_usuario_bp.route('/pago/epayco/confirmacion', methods=['POST'])
def epayco_confirmacion():
    # Webhook de ePayco (POST form)
    data = request.form.to_dict(flat=True)
    if not data:
        # Intentar JSON si no viene form
        data = request.get_json(silent=True) or {}

    rid = _epayco_extract_reserva_id(data)
    if not rid:
        return jsonify({'ok': True})

    reserva = Reserva.query.get(rid)
    if not reserva:
        return jsonify({'ok': True})

    if not _epayco_verify_signature(data):
        current_app.logger.warning('Firma ePayco inválida en confirmación: %s', data)
        return jsonify({'ok': False, 'error': 'invalid_signature'}), 400

    status = _epayco_map_status(data.get('x_transaction_state'))
    _apply_status_to_reserva(reserva, status)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error guardando estado reserva ePayco: %s', e)
        return jsonify({'ok': False}), 500

    return jsonify({'ok': True})
