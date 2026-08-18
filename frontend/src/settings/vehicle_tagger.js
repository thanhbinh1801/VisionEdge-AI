/**
 * Vehicle Whitelist / Blacklist Tagging Tool
 * SentriAI Mini Settings Module (TASK-008 - Person B)
 */
export class VehicleTagger {
  constructor(containerId, vehicles = []) {
    this.container = document.getElementById(containerId);
    this.vehicles = vehicles;
  }

  tagVehicle(licensePlate, listType, ownerName = '') {
    const existing = this.vehicles.find(v => v.license_plate === licensePlate);
    if (existing) {
      existing.list_type = listType;
      existing.owner_name = ownerName;
    } else {
      this.vehicles.push({
        license_plate: licensePlate,
        list_type: listType,
        owner_name: ownerName
      });
    }
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="vehicle-tagger bg-gray-900 border border-gray-700 rounded-lg p-4 text-gray-200">
        <h3 class="text-sm font-semibold mb-3">Quản Lý Danh Sách Biển Số (Whitelist / Blacklist)</h3>
        <div class="space-y-2">
          ${this.vehicles.map(v => `
            <div class="flex items-center justify-between bg-gray-800 p-2.5 rounded border border-gray-700">
              <div>
                <span class="font-mono text-sm font-bold text-white">${v.license_plate}</span>
                <span class="text-xs text-gray-400 ml-2">(${v.owner_name || 'Unassigned'})</span>
              </div>
              <span class="px-2 py-0.5 text-xs rounded ${
                v.list_type === 'whitelist' ? 'bg-green-900/60 text-green-300 border border-green-700' :
                v.list_type === 'blacklist' ? 'bg-red-900/60 text-red-300 border border-red-700' : 'bg-gray-700 text-gray-300'
              }">${v.list_type.toUpperCase()}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}
