const Jimp = require('jimp');
const path = require('path');

async function createIcons() {
    // 1. Create Neutral Tray Icon (White Circle)
    const neutral = new Jimp(32, 32, 0x00000000);
    for (let x = 0; x < 32; x++) {
        for (let y = 0; y < 32; y++) {
            const d = Math.sqrt(Math.pow(x-16, 2) + Math.pow(y-16, 2));
            if (d < 10) neutral.setPixelColor(0xFFFFFFFF, x, y);
        }
    }
    await neutral.writeAsync(path.join(__dirname, 'assets', 'tray-icon.png'));

    // 2. Create Active Mic Icon (Pinkish/Red Circle)
    const active = new Jimp(32, 32, 0x00000000);
    for (let x = 0; x < 32; x++) {
        for (let y = 0; y < 32; y++) {
            const d = Math.sqrt(Math.pow(x-16, 2) + Math.pow(y-16, 2));
            if (d < 10) active.setPixelColor(0xFF4C8BFF, x, y); // A vibrant pink/reddish color
        }
    }
    await active.writeAsync(path.join(__dirname, 'assets', 'tray-mic.png'));
    console.log('Dual tray icons created successfully.');
}
createIcons();
