from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, current_app
from models.baseDatos import db, PlatoRestaurante, ReservaRestaurante, ReservaPlato, Usuario
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

restaurante_cart_bp = Blueprint('restaurante_cart', __name__)


def _get_cart():
    cart = session.get('rest_cart')
    if not cart:
        cart = {'items': [], 'people': 1}
        session['rest_cart'] = cart
    return cart


@restaurante_cart_bp.route('/restaurante/cart')
def view_cart():
    cart = _get_cart()
    # recompute totals
    total = 0
    for it in cart['items']:
        it['subtotal'] = round(it['precio'] * it['cantidad'], 2)
        total += it['subtotal']
    cart['total'] = round(total, 2)
    session.modified = True
    # Mostrar categorías también (para navegar de vuelta al menú)
    platos = PlatoRestaurante.query.filter_by(activo=True).order_by(PlatoRestaurante.categoria.asc(), PlatoRestaurante.orden.asc()).all()
    grupos = {}
    for p in platos:
        cat = p.categoria or 'Otros'
        grupos.setdefault(cat, []).append(p)
    categorias = ['Entradas','Principales','Postres','Bebidas']
    cat_presentes = [c for c in categorias if c in grupos]
    extra = [c for c in grupos.keys() if c not in categorias]
    categorias_final = cat_presentes + extra
    # Evitar conflicto Jinja con cart.items (método). Pasar lista explícita.
    cart_items = cart.get('items', [])
    return render_template('usuario/restaurante_cart.html', cart=cart, cart_items=cart_items, grupos=grupos, categorias=categorias_final)


@restaurante_cart_bp.route('/restaurante/cart/add', methods=['POST'])
def cart_add():
    pid = request.form.get('plato_id')
    cant = int(request.form.get('cantidad') or 1)
    if cant < 1:
        cant = 1
    plato = PlatoRestaurante.query.get(pid)
    if not plato or not plato.activo:
        flash('Plato no disponible', 'warning')
        return redirect(url_for('main.restaurante_usuario'))
    cart = _get_cart()
    # merge by plato id
    for it in cart['items']:
        if it.get('plato_id') == plato.id:
            it['cantidad'] += cant
            break
    else:
        cart['items'].append({
            'plato_id': plato.id,
            'nombre': plato.nombre,
            'precio': float(plato.precio or 0),
            'cantidad': cant,
        })
    session.modified = True
    return redirect(url_for('restaurante_cart.view_cart'))


@restaurante_cart_bp.route('/restaurante/cart/update', methods=['POST'])
def cart_update():
    cart = _get_cart()
    for it in cart['items']:
        key = f"qty_{it.get('plato_id')}"
        if key in request.form:
            try:
                q = int(request.form.get(key) or 1)
            except Exception:
                q = 1
            it['cantidad'] = max(1, q)
    try:
        ppl = int(request.form.get('people') or 1)
        cart['people'] = max(1, ppl)
    except Exception:
        pass
    session.modified = True
    return redirect(url_for('restaurante_cart.view_cart'))


@restaurante_cart_bp.route('/restaurante/cart/remove', methods=['POST'])
def cart_remove():
    cart = _get_cart()
    pid = request.form.get('plato_id')
    if pid:
        try:
            pid = int(pid)
        except Exception:
            pid = None
    if pid is not None:
        cart['items'] = [it for it in cart['items'] if it.get('plato_id') != pid]
    session.modified = True
    return redirect(url_for('restaurante_cart.view_cart'))


def _gen_ticket_number():
    return datetime.utcnow().strftime('RT%Y%m%d%H%M%S')


@restaurante_cart_bp.route('/restaurante/reservar', methods=['POST'])
def reservar_restaurante():
    cart = _get_cart()
    if not cart['items']:
        flash('Tu carrito está vacío.', 'warning')
        return redirect(url_for('main.restaurante_usuario'))

    # Usuario/cliente
    uid = session.get('user', {}).get('idUsuario') or session.get('user', {}).get('id')
    nombre = request.form.get('nombre') or session.get('user', {}).get('usuario')
    telefono = request.form.get('telefono') or session.get('user', {}).get('telefono')
    try:
        cupo = int(request.form.get('cupo') or cart.get('people') or 1)
    except Exception:
        cupo = cart.get('people') or 1

    # Calcular total
    total = 0
    for it in cart['items']:
        subtotal = float(it['precio']) * int(it['cantidad'])
        total += subtotal

    reserva = ReservaRestaurante(
        usuario_id=uid,
        nombre_cliente=nombre,
        telefono_cliente=telefono,
        cupo_personas=cupo,
        fecha_reserva=datetime.utcnow(),
        estado='Pendiente',
        ticket_numero=_gen_ticket_number(),
        total=round(total, 2)
    )
    db.session.add(reserva)
    db.session.flush()  # obtener id

    # Detalle
    for it in cart['items']:
        rp = ReservaPlato(
            reserva_id=reserva.id,
            plato_id=it.get('plato_id'),
            nombre_plato=it.get('nombre'),
            precio_unitario=float(it.get('precio') or 0),
            cantidad=int(it.get('cantidad') or 1),
            subtotal=float(it.get('precio') or 0) * int(it.get('cantidad') or 1)
        )
        db.session.add(rp)

    db.session.commit()

    # Generar PDF en memoria
    pdf_bytes = _build_ticket_pdf(reserva)
    # Guardar opcionalmente a disco (instance/uploads/tickets), compatible con /media
    try:
        import os
        tickets_dir = os.path.join(current_app.instance_path, 'uploads', 'tickets')
        os.makedirs(tickets_dir, exist_ok=True)
        path = os.path.join(tickets_dir, f"{reserva.ticket_numero}.pdf")
        with open(path, 'wb') as f:
            f.write(pdf_bytes.getvalue())
        reserva.file_ticket = f"uploads/tickets/{reserva.ticket_numero}.pdf"
        db.session.commit()
    except Exception as e:
        current_app.logger.warning('No se pudo persistir ticket en disco: %s', e)

    # Vaciar carrito tras crear la reserva
    session['rest_cart'] = {'items': [], 'people': 1}

    pdf_bytes.seek(0)
    return send_file(pdf_bytes, mimetype='application/pdf', as_attachment=True, download_name=f"{reserva.ticket_numero}.pdf")


def _build_ticket_pdf(reserva: ReservaRestaurante):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont('Helvetica-Bold', 16)
    c.drawString(40, y, 'Reserva Restaurante - Ticket')
    y -= 25
    c.setFont('Helvetica', 11)
    c.drawString(40, y, f"Ticket: {reserva.ticket_numero}")
    y -= 18
    c.drawString(40, y, f"Fecha: {reserva.fecha_reserva.strftime('%Y-%m-%d %H:%M')} UTC")
    y -= 18
    c.drawString(40, y, f"Cliente: {reserva.nombre_cliente or '-'}")
    y -= 18
    c.drawString(40, y, f"Teléfono: {reserva.telefono_cliente or '-'}")
    y -= 18
    c.drawString(40, y, f"Cupo de personas: {reserva.cupo_personas}")

    y -= 28
    c.setFont('Helvetica-Bold', 12)
    c.drawString(40, y, 'Pedido:')
    y -= 20
    c.setFont('Helvetica', 11)
    for it in reserva.items:
        line = f"- {it.nombre_plato} x{it.cantidad}  ${it.subtotal:,.0f}"
        c.drawString(50, y, line)
        y -= 16
        if y < 60:
            c.showPage()
            y = height - 50
    y -= 10
    c.setFont('Helvetica-Bold', 12)
    c.drawString(40, y, f"Total a pagar en el lugar: ${reserva.total:,.0f} COP")

    y -= 30
    c.setFont('Helvetica-Oblique', 10)
    c.drawString(40, y, 'Presenta este ticket al llegar para validar tu reserva.')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
