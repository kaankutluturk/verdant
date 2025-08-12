(function(){
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.style.display === 'inline-flex';
      nav.style.display = open ? 'none' : 'inline-flex';
    });
  }
  
  // Waitlist form
  const form = document.getElementById('waitlist-form');
  const emailInput = document.getElementById('waitlist-email');
  const msg = document.getElementById('waitlist-message');
  const FORM_ENDPOINT = 'https://formspree.io/f/your-form-id'; // TODO: replace with your Formspree ID
  
  function setMessage(text, ok = false) {
    if (!msg) return;
    msg.textContent = text;
    msg.style.color = ok ? '#5bd174' : '#9fb1bd';
  }
  
  if (form && emailInput) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = emailInput.value.trim();
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setMessage('Please enter a valid email address.');
        emailInput.focus();
        return;
      }
      setMessage('Submitting…');
      try {
        const payload = new FormData(form);
        const res = await fetch(FORM_ENDPOINT, { method: 'POST', body: payload, headers: { 'Accept': 'application/json' }});
        if (res.ok) {
          setMessage('You are on the list. Thank you! ✅', true);
          form.reset();
        } else {
          setMessage('Something went wrong. Please try again later.');
        }
      } catch (err) {
        setMessage('Network error. Please try again.');
      }
    });
  }
})(); 