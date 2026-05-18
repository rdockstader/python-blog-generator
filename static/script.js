const COPY_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
const CHECK_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

function isDark() {
  const stored = localStorage.getItem('theme');
  if (stored) return stored === 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  const sun = document.getElementById('theme-icon-sun');
  const moon = document.getElementById('theme-icon-moon');
  if (sun) sun.style.display = dark ? 'block' : 'none';
  if (moon) moon.style.display = dark ? 'none' : 'block';
}

document.addEventListener('DOMContentLoaded', () => {
  applyTheme(isDark());

  const toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const dark = !isDark();
      localStorage.setItem('theme', dark ? 'dark' : 'light');
      applyTheme(dark);
    });
  }

  document.querySelectorAll('pre').forEach(pre => {
    const code = pre.querySelector('code');
    if (!code) return;

    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.innerHTML = COPY_ICON;
    btn.setAttribute('aria-label', 'Copy code');
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(code.textContent).then(() => {
        btn.innerHTML = CHECK_ICON;
        setTimeout(() => { btn.innerHTML = COPY_ICON; }, 1500);
      });
    });
    pre.appendChild(btn);
  });
});
