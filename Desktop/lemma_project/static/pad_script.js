// static/pad_script.js
document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('editor');
    const status = document.getElementById('status');
    
    // Получаем ID доски из URL, если его нет - создаем новый
    let boardId = window.location.pathname.split('/')[2];
    if (!boardId) {
        boardId = Math.random().toString(36).substring(2, 15);
        window.history.replaceState({}, document.title, `/pad/${boardId}`);
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${boardId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        status.textContent = `Подключено к доске: ${boardId}`;
        status.style.color = '#28a745';
    };

    ws.onmessage = (event) => {
        // Обновляем текст только если он отличается, чтобы не сбивать курсор
        if (editor.value !== event.data) {
            editor.value = event.data;
        }
    };

    ws.onclose = () => {
        status.textContent = 'Соединение потеряно. Попробуйте обновить страницу.';
        status.style.color = '#dc3545';
    };

    ws.onerror = () => {
        status.textContent = 'Ошибка соединения.';
        status.style.color = '#dc3545';
    };

    // Функция Debounce: выполняет другую функцию только после паузы
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Создаем "умную" функцию отправки с задержкой в 300мс
    const debouncedSend = debounce((text) => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(text);
        }
    }, 300);

    // Слушаем ввод текста и вызываем "умную" функцию
    editor.addEventListener('input', () => {
        debouncedSend(editor.value);
    });
});