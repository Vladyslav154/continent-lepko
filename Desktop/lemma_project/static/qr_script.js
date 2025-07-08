document.addEventListener('DOMContentLoaded', () => {
    const qrInput = document.getElementById('qr-input');
    const qrCodeContainer = document.getElementById('qrcode-container');
    let qrcode = null;

    function generateQrCode(text) {
        // Очищаем предыдущий код
        qrCodeContainer.innerHTML = '';

        if (text.trim() === '') {
            return; // Не генерируем код для пустого текста
        }

        // Создаем новый экземпляр QR-кода
        qrcode = new QRCode(qrCodeContainer, {
            text: text,
            width: 200,
            height: 200,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.H
        });
    }

    // Генерируем QR-код при вводе
    qrInput.addEventListener('input', () => {
        generateQrCode(qrInput.value);
    });

    // Генерируем пример при первой загрузке
    generateQrCode('https://' + window.location.hostname);
    qrInput.value = 'https://' + window.location.hostname;
});