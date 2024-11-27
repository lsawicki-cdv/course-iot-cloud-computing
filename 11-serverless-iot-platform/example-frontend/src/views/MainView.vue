<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useDiagramStore } from '@/stores/diagramStore';
import BtnGo from '@/components/BtnGo.vue';
  const diagramStore = useDiagramStore();

  const isErrorLoading = ref(false);
  const isLoading = ref(false)
  onMounted(async ()=> {
    isLoading.value = true;
    const [isLineLoaded] = await Promise.all([
      diagramStore.getLineChartData()
    ]) 

    if (!isLineLoaded) {
      isLoading.value = false;
      isErrorLoading.value = true; 
      setTimeout(() => {
        isErrorLoading.value = false;
    }, 1500);
      return;
    }

    isLoading.value = false;
    isErrorLoading.value = false;
})
</script>

<template>
  <nav class="nav">
    <btn-go 
      text="Line Diagram"
      route="line"
    />
  </nav>
  <p 
    v-if="isLoading"
    class="loading"
  >
      loading...
  </p>
  <div 
    v-if="isErrorLoading"
    class="error_msg"
  >
    An error detected, please try again later
  </div>
</template>

<style lang="scss">
.nav {
  display: flex;
  flex-direction: row;
  width: 50%;
  height: 5%;
  justify-content: space-between;
  padding: 10px 20px;
  border-radius: 7px;
}
.loading {
  position: absolute;
  top: 55%;
  color: #fff;
  font-family: 'Courier New', Courier, monospace;
}
.error_msg {
  position: absolute;
  bottom: 30px;
  padding: 8px 18px;
  background-color: #dd2d4a;
  color: #fff;
  border-radius: 10px;
  font-size: small;
  font-family: 'Courier New', Courier, monospace;
}
</style>
