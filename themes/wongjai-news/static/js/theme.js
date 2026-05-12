// Theme toggle — persists in localStorage
(function(){
  var btn = document.getElementById('theme-toggle');
  if(!btn) return;

  var saved = localStorage.getItem('wj-theme');
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = saved || 'dark';

  document.documentElement.setAttribute('data-theme', theme);
  updateIcon();

  function updateIcon(){
    btn.textContent = theme === 'dark' ? '🌙' : '☀️';
  }

  btn.addEventListener('click', function(){
    theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('wj-theme', theme);
    updateIcon();
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e){
    if(!localStorage.getItem('wj-theme')){
      theme = e.matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', theme);
      updateIcon();
    }
  });
})();
