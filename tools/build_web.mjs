// Use the native project's local Python on Windows and Python 3 on build hosts.
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const local = resolve(root, '.tools/python/python.exe');
const python = existsSync(local) ? local : (process.platform === 'win32' ? 'python' : 'python3');
const result = spawnSync(python, ['tools/build_web.py'], {cwd: root, stdio: 'inherit'});
if (result.error) console.error(`Python 3 is required to prepare the web player: ${result.error.message}`);
process.exit(result.status ?? 1);
