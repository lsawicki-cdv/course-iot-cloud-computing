import type { IDiagramStoreState } from '@/types/IDiagramStoreState'
import type { ILineData } from '@/types/ILineData'
import axios from 'axios'
import { defineStore } from 'pinia'

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
        const resultLineData = await axios.get(
          'https://cdv-iot-platform-functions.azurewebsites.net/api/device?device_id=my-new-device-1&code=PYWCoOZU21n1WVuHnK4vIE8PpmqM38_8ANpK9PYtF9jSAzFu5JnqIA%3D%3D'
        )
        if (resultLineData) {
          this.lineData = resultLineData.data
          return isSuccess
        }

        return !isSuccess
      } catch (err) {
        return !isSuccess
      }
    }
  }
})
