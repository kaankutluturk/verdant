(function(){
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.style.display === 'inline-flex';
      nav.style.display = open ? 'none' : 'inline-flex';
    });
  }
  // Improve details summary keyboard focus style (optional)
  document.querySelectorAll('details > summary').forEach(s => {
    s.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        s.parentElement.open = !s.parentElement.open;
      }
    });
  });
})(); 