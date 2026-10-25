/* The browser wrapper loads the unchanged, hash-verified native cartridge. */
(() => {
  'use strict';
  const status = document.querySelector('#status');
  const retry = document.querySelector('#retry');
  const release = window.ABAQUS_RELEASE;
  document.querySelector('#version').textContent = release ? `v${release.version}` : '';
  retry.addEventListener('click', () => window.location.reload());

  const fail = () => {
    status.textContent = 'Could not load the game. Check your connection and try again.';
    retry.hidden = false;
  };
  if (!release || typeof WebAssembly !== 'object') {
    status.textContent = 'This browser cannot start the player. Try a current browser or download the ROM.';
    return;
  }

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
  window.EJS_startButtonName = 'Play game';
  window.EJS_startOnLoaded = false;
  window.EJS_threads = false;
  window.EJS_disableDatabases = true;
  window.EJS_volume = 0.6;
  window.EJS_defaultOptions = {menubarBehavior: 'anywhere'};
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
    status.textContent = 'Ready. Click Play game to begin.';
    const play = document.querySelector('.ejs_start_button');
    play.setAttribute('role', 'button');
    play.tabIndex = 0;
    play.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        play.click();
      }
    });
    window.EJS_emulator.on('start-clicked', () => {
      status.textContent = 'Loading the game…';
      const errors = new MutationObserver(() => {
        if (document.querySelector('.ejs_error_text')) { fail(); errors.disconnect(); }
        if (window.EJS_emulator.started) errors.disconnect();
      });
      errors.observe(document.querySelector('#game'), {childList: true, subtree: true, attributes: true, attributeFilter: ['class']});
    });
  };
  window.EJS_onGameStart = () => {
    status.textContent = 'Enter to start · X to confirm · Z to go back';
    document.querySelector('#game').focus({preventScroll: true});
    retry.hidden = true;
  };
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
