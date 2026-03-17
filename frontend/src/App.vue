<template>
  <div id="layout">
    <nav>
      <span class="brand">📊 Evaluaciones UVG</span>
      <router-link to="/">Inicio</router-link>
      <router-link to="/upload">Subir</router-link>
      <router-link to="/reports">Reportes</router-link>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #333; }
#layout { display: flex; flex-direction: column; min-height: 100vh; }
nav { background: #1a1a2e; padding: 1rem 2rem; display: flex; gap: 1.5rem; align-items: center; }
.brand { color: #e94560; font-weight: 700; font-size: 1.05rem; margin-right: auto; }
nav a { color: #fff; text-decoration: none; font-weight: 500; }
nav a.router-link-active { border-bottom: 2px solid #e94560; }
main { flex: 1; padding: 2rem; max-width: 1100px; margin: 0 auto; width: 100%; }
</style>
