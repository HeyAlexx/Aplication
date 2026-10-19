const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const descriptor = process.env.ALTOIDSS_STORAGE_CONFIG || path.join(root, '..', 'catalog-storage.local.json');
if (process.env.ALTOIDSS_STORAGE_CONFIG && !fs.existsSync(descriptor)) throw Error('Descriptor de pruebas no disponible');
module.exports = fs.existsSync(descriptor) ? JSON.parse(fs.readFileSync(descriptor, 'utf8')).catalogDir : path.join(root, 'data');
