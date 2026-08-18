/**
 * Interactive Polygon Zone Editor (SVG Drag & Point Placement)
 * SentriAI Mini Settings Module (TASK-008 - Person A)
 */
export class ZoneEditor {
  constructor(containerId, initialPoints = []) {
    this.container = document.getElementById(containerId);
    this.points = initialPoints; // [[x1, y1], [x2, y2], ...]
    this.mode = 'select'; // 'select' | 'draw'
  }

  setMode(mode) {
    this.mode = mode;
    this.render();
  }

  addPoint(x, y) {
    this.points.push([x, y]);
    this.render();
  }

  getPolygonSVG() {
    if (this.points.length === 0) return '';
    const pointsStr = this.points.map(p => `${p[0]},${p[1]}`).join(' ');
    return `<polygon points="${pointsStr}" fill="rgba(59, 130, 246, 0.25)" stroke="#3B82F6" stroke-width="2" />`;
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="zone-editor-wrapper relative w-full h-96 bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
        <svg class="w-full h-full absolute inset-0 cursor-crosshair">
          ${this.getPolygonSVG()}
          ${this.points.map((p, idx) => `
            <circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#EF4444" stroke="#FFFFFF" stroke-width="1.5" data-idx="${idx}" />
          `).join('')}
        </svg>
        <div class="absolute top-2 left-2 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 flex gap-2 text-xs text-gray-200">
          <button class="px-2 py-1 bg-blue-600 rounded hover:bg-blue-500" onclick="window.zoneEditorInstance?.setMode('draw')">Draw Mode</button>
          <button class="px-2 py-1 bg-gray-700 rounded hover:bg-gray-600" onclick="window.zoneEditorInstance?.setMode('select')">Select Mode</button>
        </div>
      </div>
    `;
  }
}
