/* The browser wrapper loads the unchanged, hash-verified native cartridge. */
(() => {
  'use strict';
  const status = document.querySelector('#status');
  const retry = document.querySelector('#retry');
  const sound = document.querySelector('#enable-sound');
  const game = document.querySelector('#game');
  const release = window.ABAQUS_RELEASE;
  document.querySelector('#version').textContent = release ? `v${release.version}` : '';
  retry.addEventListener('click', () => window.location.reload());

  let started = false;
  let failed = false;
  let soundEnabled = false;
  let unlocking = false;
  const fail = () => {
    if (started) return;
    failed = true;
    status.textContent = 'Could not load the game. Check your connection and try again.';
    retry.hidden = false;
    game.setAttribute('aria-busy', 'false');
  };
  if (!release) { fail(); return; }
  if (typeof WebAssembly !== 'object') {
    status.textContent = 'This browser cannot start the player. Try a current browser or download the ROM.';
    game.setAttribute('aria-busy', 'false');
    return;
  }

  // Boot video immediately. Sound is separate: browsers may suspend Web Audio
  // until a trusted keyboard/touch/click gesture. Never consume that game input.
  const unlockSound = async () => {
    if (soundEnabled || unlocking || !started) return;
    const context = window.EJS_emulator?.Module?.AL?.currentCtx?.audioCtx;
    if (!context) return;
    unlocking = true;
    try {
      await context.resume();
      if (context.state !== 'running') return;
      window.EJS_emulator.volume = 0.6;
      window.EJS_emulator.setVolume(0.6);
      soundEnabled = true;
      sound.hidden = true;
      document.removeEventListener('keydown', firstInteraction, true);
      document.removeEventListener('pointerdown', firstInteraction, true);
      document.removeEventListener('touchstart', firstInteraction, true);
    } catch (_) {
      sound.textContent = 'Try enabling sound';
    } finally {
      unlocking = false;
    }
  };
  const firstInteraction = (event) => {
    if (!event.isTrusted) return;
    if (event.type === 'keydown' && (event.repeat || event.ctrlKey || event.metaKey || event.altKey || ['Shift', 'Control', 'Alt', 'Meta', 'Tab', 'Escape'].includes(event.key))) return;
    unlockSound();
  };
  sound.addEventListener('click', unlockSound);
  document.addEventListener('keydown', firstInteraction, true);
  document.addEventListener('pointerdown', firstInteraction, true);
  document.addEventListener('touchstart', firstInteraction, {capture: true, passive: true});

  // libretro SNES indices: B=0, Y=1, Select=2, Start=3, A=8, X=9.
  // Blank unused bindings, including fast-forward/slow-motion hotkeys.
  const controls = (keys) => {
    const pad = Object.fromEntries(Array.from({length: 30}, (_, id) => [id, {value: '', value2: ''}]));
    const gamepad = {0: 'BUTTON_2', 1: 'BUTTON_4', 2: 'SELECT', 3: 'START', 4: 'DPAD_UP', 5: 'DPAD_DOWN', 6: 'DPAD_LEFT', 7: 'DPAD_RIGHT', 8: 'BUTTON_1', 9: 'BUTTON_3', 10: 'LEFT_TOP_SHOULDER', 11: 'RIGHT_TOP_SHOULDER'};
    for (const [id, key] of Object.entries(keys)) pad[id] = {value: key, value2: gamepad[id]};
    return pad;
  };
  window.EJS_player = '#game';
  window.EJS_core = 'snes9x';
  window.EJS_pathtodata = './' + release.emulator_path;
  window.EJS_gameUrl = `./abaqus-after-hours.sfc?v=${release.rom_sha256}`;
  window.EJS_gameName = 'Abaqus After Hours';
  window.EJS_gameID = `abaqus-after-hours-${release.version}`;
  window.EJS_language = 'en-US';
  window.EJS_disableAutoLang = false;
  window.EJS_color = '#e6bc62';
  window.EJS_backgroundColor = '#191814';
  window.EJS_backgroundImage = new URL('./poster.png', window.location.href).href;
  window.EJS_backgroundBlur = false;
  window.EJS_startOnLoaded = true;
  window.EJS_threads = false;
  window.EJS_disableDatabases = true;
  // Saved emulator volumes must not bypass the first-interaction sound gate.
  window.EJS_disableLocalStorage = true;
  window.EJS_volume = 0;
  window.EJS_defaultOptions = {vsync: 'disabled', menubarBehavior: 'anywhere', 'virtual-gamepad': navigator.maxTouchPoints > 0 ? 'enabled' : 'disabled'};
  window.EJS_defaultControls = {
    0: controls({0: 'z', 1: 'a', 2: 'shift', 3: 'enter', 4: 'up arrow', 5: 'down arrow', 6: 'left arrow', 7: 'right arrow', 8: 'x', 9: 's', 10: 'd', 11: 'f'}),
    1: controls({0: 'numpad 1', 1: 'numpad 7', 2: 'q', 3: 'space', 4: 'i', 5: 'k', 6: 'j', 7: 'l', 8: 'numpad 2', 9: 'numpad 8', 10: 'u', 11: 'o'}),
    2: controls({}),
    3: controls({})
  };
  window.EJS_VirtualGamepadSettings = [
    {type: 'button', text: 'X', id: 'x', location: 'right', left: 40, bold: true, input_value: 9},
    {type: 'button', text: 'Y', id: 'y', location: 'right', top: 40, bold: true, input_value: 1},
    {type: 'button', text: 'A', id: 'a', location: 'right', left: 81, top: 40, bold: true, input_value: 8},
    {type: 'button', text: 'B', id: 'b', location: 'right', left: 40, top: 80, bold: true, input_value: 0},
    {type: 'dpad', id: 'dpad', location: 'left', left: '50%', top: '50%', joystickInput: false, inputValues: [4, 5, 6, 7]},
    {type: 'button', text: 'Start', id: 'start', location: 'center', left: 60, fontSize: 15, block: true, input_value: 3},
    {type: 'button', text: 'Select', id: 'select', location: 'center', left: -5, fontSize: 15, block: true, input_value: 2},
    {type: 'button', text: 'L', id: 'l', location: 'left', left: 3, top: -100, bold: true, block: true, input_value: 10},
    {type: 'button', text: 'R', id: 'r', location: 'right', right: 3, top: -100, bold: true, block: true, input_value: 11}
  ];
  window.EJS_Buttons = {
    playPause: true, restart: true, mute: true, fullscreen: true, gamepad: true, volume: true,
    settings: false, saveState: false, loadState: false, screenRecord: false, cheat: false,
    saveSavFiles: false, loadSavFiles: false, quickSave: false, quickLoad: false,
    screenshot: false, cacheManager: false, exitEmulation: false
  };
  window.EJS_ready = () => {
    if (!failed && !started) status.textContent = 'Loading the native title…';
  };
  window.EJS_onGameStart = () => {
    started = true;
    clearTimeout(startupTimeout);
    errors.disconnect();
    status.textContent = 'Choose your mode, fighters and arena. The fight starts automatically.';
    game.setAttribute('aria-busy', 'false');
    game.focus({preventScroll: true});
    // EmulatorJS opens its toolbar at boot; on small screens that panel covers
    // the native Start touch control. Leave it available through its menu icon.
    window.EJS_emulator.menu.close();
    // The pinned gamepad handler polls once in its constructor, before its
    // connected listener is registered. Assign already-connected pads using
    // the same first-free-player policy as its later hotplug events.
    const emulator = window.EJS_emulator;
    for (const pad of emulator.gamepad.gamepads) {
      const id = `${pad.id}_${pad.index}`;
      if (emulator.gamepadSelection.includes(id)) continue;
      const player = emulator.gamepadSelection.slice(0, 2).indexOf('');
      if (player < 0) break;
      emulator.gamepadSelection[player] = id;
    }
    emulator.updateGamepadLabels();
    retry.hidden = true;
    sound.hidden = false;
  };
  // Observe before appending the loader: automatic core loading starts before
  // EJS_ready, so errors must not depend on the removed start-clicked event.
  const errors = new MutationObserver(() => {
    if (document.querySelector('.ejs_error_text')) fail();
  });
  errors.observe(game, {childList: true, subtree: true, attributes: true, attributeFilter: ['class']});
  const startupTimeout = setTimeout(fail, 90000);
  window.addEventListener('error', (event) => {
    if (event.target instanceof HTMLScriptElement || event.target instanceof HTMLLinkElement || event.filename?.includes('/emulator/')) fail();
  }, true);
  window.addEventListener('unhandledrejection', () => {
    if (window.EJS_emulator?.failedToStart) fail();
  });
  const loader = document.createElement('script');
  loader.src = window.EJS_pathtodata + 'loader.js';
  loader.onerror = fail;
  document.head.append(loader);
})();
