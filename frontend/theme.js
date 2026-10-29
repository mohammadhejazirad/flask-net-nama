try {
  const theme = localStorage.getItem('theme') || 'system';
  document.documentElement.dataset.theme = theme === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
  const locale = localStorage.getItem('locale') || 'fa';
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === 'fa' ? 'rtl' : 'ltr';
} catch {}
