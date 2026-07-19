/*
  AETHELX Trust Badge — embeddable widget
  Usage: <script src="https://aethelx.com/badge.js" data-theme="dark"></script>
  Place this tag anywhere on a page; the badge renders right where the
  script tag sits. Self-contained inline styles so it won't clash with
  the host site's CSS.
*/
(function () {
  var currentScript = document.currentScript;
  var theme = (currentScript && currentScript.getAttribute('data-theme')) || 'dark';

  var isDark = theme !== 'light';
  var bg = isDark ? '#07071a' : '#ffffff';
  var border = isDark ? 'rgba(0,229,255,0.35)' : 'rgba(0,180,210,0.35)';
  var text = isDark ? '#eaeaf0' : '#0a0a12';
  var accent = '#00c2d6';

  var link = document.createElement('a');
  link.href = 'https://aethelx.com/?ref=badge';
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.setAttribute('aria-label', 'Verified by AETHELX — AI Trust Infrastructure');
  link.style.cssText = [
    'display:inline-flex',
    'align-items:center',
    'gap:6px',
    'padding:6px 12px',
    'border-radius:999px',
    'background:' + bg,
    'border:1px solid ' + border,
    'text-decoration:none',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
    'font-size:12px',
    'font-weight:600',
    'color:' + text,
    'line-height:1',
    'transition:opacity 0.2s',
    'box-shadow:0 2px 8px rgba(0,0,0,0.08)'
  ].join(';');
  link.onmouseover = function () { link.style.opacity = '0.85'; };
  link.onmouseout = function () { link.style.opacity = '1'; };

  var icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('width', '14');
  icon.setAttribute('height', '14');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.innerHTML = '<path d="M12 2L2 7l10 5 10-5-10-5z" fill="' + accent + '"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="' + accent + '" stroke-width="1.5" fill="none"/>';

  var label = document.createElement('span');
  label.textContent = 'Verified by AETHELX';

  link.appendChild(icon);
  link.appendChild(label);

  if (currentScript && currentScript.parentNode) {
    currentScript.parentNode.insertBefore(link, currentScript.nextSibling);
  } else {
    document.write(link.outerHTML);
  }
})();
