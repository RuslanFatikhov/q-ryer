/**
 * Управление лоадером страницы
 * Скрывает лоадер через 3 секунды после полной загрузки
 */
window.addEventListener('load', () => {
  const loader = document.getElementById('pageLoader');
  if (loader) {
    // Ждем 3 секунды после загрузки страницы
    setTimeout(() => {
      loader.classList.add('hidden');
      console.log('✅ Скрываем лоадер');
      
      // Удаляем из DOM после завершения анимации (0.5s)
      setTimeout(() => {
        loader.remove();
      }, 500);
    }, 3000); // 3 секунды
  }
});
