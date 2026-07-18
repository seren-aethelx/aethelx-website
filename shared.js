// AETHELX — Shared JS (nav auth, waitlist, notifications, reveal)
// Loaded on every page.

const API_BASE = 'https://aggnes99-lumora-backend.hf.space';

function showNotif(msg, color = 'var(--cyan)') {
  const n = document.getElementById('notif');
  if (!n) return;
  n.textContent = msg;
  n.style.borderColor = color;
  n.style.color = color;
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 3000);
}

// ─── SCROLL REVEAL ───
document.addEventListener('DOMContentLoaded', () => {
  const revealEls = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  revealEls.forEach(el => observer.observe(el));
});

// ─── AUTH MODAL ───
function openAuth(tab) {
  document.getElementById('auth-modal').classList.add('open');
  switchTab(tab);
}
function closeAuth() {
  document.getElementById('auth-modal').classList.remove('open');
  document.getElementById('auth-success').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('signup-form').style.display = 'none';
  switchTab('login');
}
function switchTab(tab) {
  document.getElementById('login-form').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('signup-form').style.display = tab === 'signup' ? 'block' : 'none';
  document.getElementById('auth-success').style.display = 'none';
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-signup').classList.toggle('active', tab === 'signup');
}

// NOTE: Login still checks against localStorage for now, since the backend
// /signup route only stores new accounts — a matching /login (that checks
// the password hash in Supabase) would be the next piece to add if you want
// full login support across devices/browsers.
function handleLogin() {
  const email = document.getElementById('login-email').value.trim();
  const pass = document.getElementById('login-pass').value;
  if (!email || !pass) { showNotif('⚠ Enter email and password', 'var(--red)'); return; }
  const users = JSON.parse(localStorage.getItem('AETHELX_users') || '{}');
  if (!users[email] || users[email].pass !== pass) { showNotif('⚠ Invalid credentials', 'var(--red)'); return; }
  localStorage.setItem('AETHELX_current', JSON.stringify({ email, name: users[email].name }));
  document.getElementById('login-form').style.display = 'none';
  document.getElementById('success-msg').textContent = `WELCOME BACK, ${users[email].name.toUpperCase()}!`;
  document.getElementById('auth-success').style.display = 'block';
  setTimeout(closeAuth, 2000);
  showNotif('✓ Logged in successfully', 'var(--green)');
}

// Signup now calls the backend, which saves the account into the Supabase
// "users" table (password is hashed server-side before storage).
async function handleSignup() {
  const name = document.getElementById('signup-name').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const pass = document.getElementById('signup-pass').value;
  if (!name || !email || pass.length < 8) { showNotif('⚠ Fill all fields (min 8 char password)', 'var(--red)'); return; }

  const btn = document.querySelector('#signup-form .btn-auth');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password: pass })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // Keep a local copy too, so login on this same browser still works
    // immediately (see handleLogin note above).
    const users = JSON.parse(localStorage.getItem('AETHELX_users') || '{}');
    users[email] = { name, pass };
    localStorage.setItem('AETHELX_users', JSON.stringify(users));
    localStorage.setItem('AETHELX_current', JSON.stringify({ email, name }));

    document.getElementById('signup-form').style.display = 'none';
    document.getElementById('success-msg').textContent = `WELCOME TO AETHELX, ${name.toUpperCase()}!`;
    document.getElementById('auth-success').style.display = 'block';
    setTimeout(closeAuth, 2000);
    showNotif('✓ Account created!', 'var(--green)');
  } catch (err) {
    showNotif(`⚠ ${err.message}`, 'var(--red)');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ─── WAITLIST MODAL ───
function openWaitlist(plan) {
  document.getElementById('waitlist-plan-label').textContent = plan.toUpperCase() + ' PLAN';
  document.getElementById('wl-success').style.display = 'none';
  document.getElementById('wl-name').style.display = '';
  document.getElementById('wl-email').style.display = '';
  document.querySelector('[onclick="submitWaitlist()"]').style.display = '';
  document.getElementById('waitlist-modal').classList.add('open');
}
function closeWaitlist() { document.getElementById('waitlist-modal').classList.remove('open'); }

// Waitlist submissions now go straight to the backend, which saves them
// into the Supabase "waitlist" table — visible in your Supabase dashboard
// under Table Editor > waitlist.
async function submitWaitlist() {
  const name = document.getElementById('wl-name').value.trim();
  const email = document.getElementById('wl-email').value.trim();
  if (!name || !email) { showNotif('⚠ Enter name and email', 'var(--red)'); return; }
  const plan = document.getElementById('waitlist-plan-label').textContent;

  const btn = document.querySelector('[onclick="submitWaitlist()"]');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/waitlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, plan })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    document.getElementById('wl-name').style.display = 'none';
    document.getElementById('wl-email').style.display = 'none';
    if (btn) btn.style.display = 'none';
    document.getElementById('wl-success').style.display = 'block';
    showNotif('🎯 You\'re on the waitlist!', 'var(--cyan)');
    setTimeout(closeWaitlist, 3000);
  } catch (err) {
    showNotif(`⚠ ${err.message}`, 'var(--red)');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// close modals on outside click (only runs if elements exist on the page)
document.addEventListener('DOMContentLoaded', () => {
  const am = document.getElementById('auth-modal');
  if (am) am.addEventListener('click', function (e) { if (e.target === this) closeAuth(); });
  const wm = document.getElementById('waitlist-modal');
  if (wm) wm.addEventListener('click', function (e) { if (e.target === this) closeWaitlist(); });
});

// ─── FAQ ───
function toggleFaq(btn) {
  const answer = btn.nextElementSibling;
  const isOpen = btn.classList.contains('open');
  document.querySelectorAll('.faq-q').forEach(q => {
    q.classList.remove('open');
    q.nextElementSibling.classList.remove('open');
  });
  if (!isOpen) { btn.classList.add('open'); answer.classList.add('open'); }
}