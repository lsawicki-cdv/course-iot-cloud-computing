<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

    
<template>
  <main class="container">
    <RouterView />
  </main>
</template>

<style scoped>
.container {
  background: #a0c1b9;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
