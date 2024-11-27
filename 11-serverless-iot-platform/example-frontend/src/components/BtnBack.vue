<script setup lang="ts">

</script>

<template>
    <button 
        class="btn_back"
        @click="$router.push('/')"
    >
        Go back
    </button>
</template>

<style scoped>
.btn_back {
    position: absolute;
    top: 30px;
    left: 30px;
    outline: none;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    background: none;
    color: #fff;
    font-size: medium;
    font-family: 'Courier New', Courier, monospace;
}
.btn_back:hover {
    background-color: #70a0af;
}
</style>