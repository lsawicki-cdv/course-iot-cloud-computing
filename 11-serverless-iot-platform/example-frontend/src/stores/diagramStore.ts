import type { IDiagramStoreState } from '@/types/IDiagramStoreState'
import type { ILineData } from '@/types/ILineData'
import axios from 'axios'
import { defineStore } from 'pinia'
import { buildApiUrl, API_CONFIG } from '@/config/api'

export const useDiagramStore = defineStore('diagramStore', {
  state: (): IDiagramStoreState => ({
    lineData: []
  }),
  getters: {
    lineDataLabels(): string[] {
      return this.lineData.map((dataItem: ILineData) => dataItem.timestamp)
    },
    lineDataDatasetsData(): number[] {
      return this.lineData.map((dataItem: ILineData) => dataItem.temperature)
    }
  },
  actions: {
    async getLineChartData() {
      const isSuccess = true
      try {
        // Build API URL using environment configuration
        const apiUrl = buildApiUrl('/api/device', {
          device_id: API_CONFIG.deviceId
        })

        const resultLineData = await axios.get(apiUrl)
        if (resultLineData) {
          this.lineData = resultLineData.data
          return isSuccess
        }

        return !isSuccess
      } catch (err) {
        console.error('Error fetching line chart data:', err)
        return !isSuccess
      }
    }
  }
})
