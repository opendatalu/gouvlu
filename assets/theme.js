require('./less/theme.less');

// Ensure all images are copied
require.context('./img', true, /^\.\/.*\.(jpg|jpeg|png|gif|svg)$/);

import Slideout from 'slideout';


const slideout = new Slideout({
    panel: document.getElementById('panel'),
    menu: document.getElementById('menu'),
    side: 'right',
    padding: 280, // Should match less @mobile-menu-width
    tolerance: 70
});

// Toggle button
document.querySelector('.navbar-toggle').addEventListener('click', function(e) {
    slideout.toggle();
    // Prvent default menu behavior to kick in
    e.stopPropagation();
    e.preventDefault();
});


// clickable overlay
function close(ev) {
    ev.preventDefault();
    slideout.close();
}

slideout
    .on('open', function() {
        this.panel.addEventListener('click', close);
    })
    .on('beforeclose', function() {
        this.panel.removeEventListener('click', close);
    });


// Action modal close menu
document.querySelector('.mobile-menu .contribute').addEventListener('click', function(e) {
    slideout.close();
});

// Toggle submenu
Array.prototype.forEach.call(document.querySelectorAll('.mobile-menu a:not([href])'), function(el) {
    el.addEventListener('click', function(e) {
        el.parentElement.classList.toggle('open');
        e.preventDefault();
        e.stopPropagation();
    });
});
