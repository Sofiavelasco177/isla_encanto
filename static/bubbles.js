// Lightweight bubble background generator for all pages (vanilla JS)
(function(){
  function init(){
    var layer = document.getElementById('bubble-layer');
    if (!layer) return;
    // Avoid duplicates
    if (layer.dataset.ready) return;
    layer.dataset.ready = '1';
    var count = 20; // number of bubbles
    for (var i=0;i<count;i++){
      createBubble(layer, i);
    }
  }

  function rand(min, max){ return Math.random() * (max - min) + min; }

  function createBubble(layer, id){
    var el = document.createElement('div');
    el.className = 'bubble ' + (Math.random() > 0.5 ? 'blue' : 'green');
    var size = rand(80, 200);
    el.style.width = size + 'px';
    el.style.height = size + 'px';
    el.style.left = rand(0, 100) + 'vw';
    el.style.bottom = '-20vh';
    el.style.opacity = (0.2 + Math.random() * 0.3).toFixed(2);
    // Animate
    el.style.animationDelay = rand(0, 5).toFixed(2) + 's';
    el.style.animationDuration = rand(15, 25).toFixed(2) + 's';
    // Random horizontal drift and scale
    var drift = (Math.random() > 0.5 ? 1 : -1) * rand(20, 100);
    var scale = (0.5 + Math.random() * 0.6).toFixed(2);
    el.style.setProperty('--float-x', drift + 'px');
    el.style.setProperty('--float-scale', scale);
    layer.appendChild(el);
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();