const Jimp = require('jimp');
const path = require('path');

async function createIcon() {
    // Create a 16x16 white circle icon for the tray
    const image = new Jimp(32, 32, 0x00000000); // Transparent background
    
    // Draw a simple white circular "Orb" icon
    for (let x = 0; x < 32; x++) {
        for (let y = 0; y < 32; y++) {
            const distance = Math.sqrt(Math.pow(x - 16, 2) + Math.pow(y - 16, 2));
            if (distance < 10) {
                image.setPixelColor(0xFFFFFFFF, x, y); // Pure white
            } else if (distance < 12) {
                image.setPixelColor(0xFFFFFF44, x, y); // Translucent border
            }
        }
    }
    
    await image.writeAsync(path.join(__dirname, 'assets', 'tray-icon.png'));
    console.log('Tray icon PNG created.');
}

createIcon();
