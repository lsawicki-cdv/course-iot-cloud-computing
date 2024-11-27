<script setup lang="ts">
import { useDiagramStore } from '@/stores/diagramStore';
import { Line } from 'vue-chartjs'

import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
 } from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
  );

const diagramStore = useDiagramStore();

const chartData = {
        labels: diagramStore.lineDataLabels,
        datasets: [ { 
            data: diagramStore.lineDataDatasetsData,
            backgroundColor: '#a8b4a5',
            label: 'Dates',
        } ]
      }

const chartOptions = {
        maintainAspectRatio: false,
        borderColor: '#9d6a89',
      }
</script>

<template>
  <div>
    <Line 
      id="line-chart-id"
      :options="chartOptions"
      :data="chartData"
    />
  </div>
</template>

<style lang="scss">

</style>
