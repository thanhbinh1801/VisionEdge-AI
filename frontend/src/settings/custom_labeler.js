/**
 * Custom Dataset BBox Annotation & Few-shot Labeler Tool with Timeline Scrubber
 * SentriAI Mini Settings Module (TASK-008 - Person B)
 */
export class CustomLabeler {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.labels = [];
    this.currentTime = 0;
  }

  addCustomLabel(labelName, bboxCoordinates) {
    this.labels.push({
      id: `LABEL-${Date.now()}`,
      label_name: labelName,
      bbox_coordinates: bboxCoordinates,
      timestamp: this.currentTime
    });
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="custom-labeler bg-gray-900 border border-gray-700 rounded-lg p-4 text-gray-200">
        <h3 class="text-sm font-semibold mb-3">Công Cụ Khoanh BBox Mẫu Đối Tượng Custom (Few-shot Embedding)</h3>
        <div class="timeline-scrubber mb-3">
          <input type="range" min="0" max="100" value="${this.currentTime}" class="w-full h-1 bg-gray-700 rounded appearance-none cursor-pointer" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          ${this.labels.map(l => `
            <div class="bg-gray-800 p-2 rounded border border-gray-700 text-xs">
              <span class="font-bold text-blue-400">${l.label_name}</span>
              <div class="text-gray-400 text-[10px]">BBox: ${JSON.stringify(l.bbox_coordinates)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}
