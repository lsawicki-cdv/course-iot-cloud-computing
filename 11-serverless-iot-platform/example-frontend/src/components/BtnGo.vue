<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const props = defineProps<{
    text: string,
    route: string,
}>()
</script>

<template>
    <button 
      class="nav_btn"
      @click="router.push(`/diagram/${props.route}`)"
    >
    {{ props.text }}
    </button>
</template>

<style scoped>
.nav_btn {
  outline: none;
  border: none;
  border-radius: 7px;
  padding: 8px 18px;
  background: none;
  color: #fff;
  font-size: medium;
  font-family: 'Courier New', Courier, monospace;
}
.nav_btn:hover {
  background-color: #70a0af;
}
</style>