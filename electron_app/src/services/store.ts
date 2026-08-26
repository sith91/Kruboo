import Store from 'electron-store';
import keytar from 'keytar';
import { Persona } from '../models/persona';

const SERVICE_NAME = 'kruboo-ai-assistant';
const ACCOUNT_NAME = 'encryption-key';

// Retrieve or generate an encryption key via keytar
async function getEncryptionKey(): Promise<string> {
  let key = await keytar.getPassword(SERVICE_NAME, ACCOUNT_NAME);
  if (!key) {
    // Generate a random 32‑byte hex key
    key = [...Array(32)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');
    await keytar.setPassword(SERVICE_NAME, ACCOUNT_NAME, key);
  }
  return key;
}

let storePromise: Promise<Store<any>> | null = null;
async function getStore(): Promise<Store<any>> {
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

export async function getPersonas(): Promise<Persona[]> {
  const store = await getStore();
  return (store.get('personas') as Persona[]) ?? [];
}

export async function savePersona(p: Persona): Promise<void> {
  const store = await getStore();
  const existing = (store.get('personas') as Persona[]) ?? [];
  const idx = existing.findIndex((x) => x.id === p.id);
  if (idx >= 0) existing[idx] = p; else existing.push(p);
  store.set('personas', existing);
}

export async function deletePersona(id: string): Promise<void> {
  const store = await getStore();
  const existing = (store.get('personas') as Persona[]) ?? [];
  const filtered = existing.filter((x) => x.id !== id);
  store.set('personas', filtered);
  const active = store.get('activePersona') as string;
  if (active === id) store.set('activePersona', '');
}

export async function setActivePersona(id: string): Promise<void> {
  const store = await getStore();
  store.set('activePersona', id);
}

export async function getActivePersona(): Promise<Persona | null> {
  const store = await getStore();
  const id = store.get('activePersona') as string;
  if (!id) return null;
  const personas = (store.get('personas') as Persona[]) ?? [];
  return personas.find((p) => p.id === id) ?? null;
}
