const Store = require('electron-store');
const keytar = require('keytar');

const SERVICE_NAME = 'kruboo-ai-assistant';
const ACCOUNT_NAME = 'encryption-key';

// Retrieve or generate an encryption key via keytar
async function getEncryptionKey() {
  let key = await keytar.getPassword(SERVICE_NAME, ACCOUNT_NAME);
  if (!key) {
    // Generate a random 32-byte hex key
    key = [...Array(32)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');
    await keytar.setPassword(SERVICE_NAME, ACCOUNT_NAME, key);
  }
  return key;
}

let storePromise = null;
async function getStore() {
  if (!storePromise) {
    storePromise = (async () => {
      const encKey = await getEncryptionKey();
      return new Store({
        name: 'kruboo-data',
        encryptionKey: encKey,
        schema: {
          personas: { type: 'array', default: [] },
          activePersona: { type: 'string', default: '' }
        }
      });
    })();
  }
  return storePromise;
}

async function getPersonas() {
  const store = await getStore();
  return store.get('personas') ?? [];
}

async function savePersona(p) {
  const store = await getStore();
  const existing = store.get('personas') ?? [];
  const idx = existing.findIndex((x) => x.id === p.id);
  if (idx >= 0) existing[idx] = p; else existing.push(p);
  store.set('personas', existing);
}

async function deletePersona(id) {
  const store = await getStore();
  const existing = store.get('personas') ?? [];
  const filtered = existing.filter((x) => x.id !== id);
  store.set('personas', filtered);
  const active = store.get('activePersona');
  if (active === id) store.set('activePersona', '');
}

async function setActivePersona(id) {
  const store = await getStore();
  store.set('activePersona', id);
}

async function getActivePersona() {
  const store = await getStore();
  const id = store.get('activePersona');
  if (!id) return null;
  const personas = store.get('personas') ?? [];
  return personas.find((p) => p.id === id) ?? null;
}

module.exports = { getPersonas, savePersona, deletePersona, setActivePersona, getActivePersona };
