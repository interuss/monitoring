{# Shared canvas viewport. The including script supplies data.scenario_start/end,
   draw(), hitTest(x, y), and updateTooltip(event, item). Hit-test items may expose
   href for click navigation. Set timeline_horizontal to enable horizontal lanes
   (also supplying X_OPS_START). Initialize with resizeCanvas() after setup. #}
      const container = document.getElementById('timeline-container');
      const canvas = document.getElementById('timeline-canvas');
      const ctx = canvas.getContext('2d');
      const tooltip = document.getElementById('tooltip');

      const scenarioStart = data.scenario_start;
      const scenarioEnd = data.scenario_end;
      const fullDuration = scenarioEnd - scenarioStart;
      const minDuration = Math.min(0.05, fullDuration); // 50ms min zoom window

      // Visible time window [viewT0, viewT1]
      let viewT0 = scenarioStart;
      let viewT1 = scenarioEnd;

      // Layout constants
      const H_HEADER = 36;
      const W_SCROLLBAR = 24;
      const H_HSCROLLBAR = {{ 14 if timeline_horizontal else 0 }};

      let width = 0;
      let height = 0;
      let dpr = window.devicePixelRatio || 1;

      let hoveredItem = null;
      let drawPending = false;

      // Multiple input events can arrive before the browser paints a frame.
      function requestDraw() {
        if (drawPending) return;
        drawPending = true;
        requestAnimationFrame(() => {
          drawPending = false;
          draw();
        });
      }

      function setHoveredItem(item) {
        // Hit tests return new wrappers; compare the underlying report objects.
        const changed = item?.type !== hoveredItem?.type ||
          item?.op !== hoveredItem?.op ||
          item?.action !== hoveredItem?.action ||
          (item?.type === 'time' && item.y !== hoveredItem?.y);
        hoveredItem = item;
        if (changed) requestDraw();
      }

      // Drag & Interaction state
      let isDraggingMain = false;
      let isDraggingScrollbar = false;
      let dragAnchorY = 0;
      let dragAnchorTime = 0;
      let dragStartT0 = 0;
      let dragStartT1 = 0;
      let dragWithShift = false;
      {% if timeline_horizontal %}
      {% include "timeline/horizontal.js" %}
      {% endif %}

      function clampView() {
        let span = viewT1 - viewT0;
        if (span >= fullDuration) {
          viewT0 = scenarioStart;
          viewT1 = scenarioEnd;
          return;
        }
        if (span < minDuration) {
          const center = (viewT0 + viewT1) / 2;
          span = Math.min(minDuration, fullDuration);
          viewT0 = center - span / 2;
          viewT1 = center + span / 2;
        }
        if (viewT0 < scenarioStart) {
          viewT0 = scenarioStart;
          viewT1 = viewT0 + span;
        }
        if (viewT1 > scenarioEnd) {
          viewT1 = scenarioEnd;
          viewT0 = viewT1 - span;
        }
        if (viewT0 < scenarioStart) {
          viewT0 = scenarioStart;
        }
      }

      function resizeCanvas() {
        const rect = container.getBoundingClientRect();
        width = rect.width;
        height = rect.height;
        dpr = window.devicePixelRatio || 1;

        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        ctx.resetTransform();
        ctx.scale(dpr, dpr);

        requestDraw();
      }

      window.addEventListener('resize', resizeCanvas);

      function timelineHeight() {
        return Math.max(10, height - H_HEADER - H_HSCROLLBAR);
      }

      function timeToY(t) {
        const timelineH = timelineHeight();
        return H_HEADER + ((t - viewT0) / (viewT1 - viewT0)) * timelineH;
      }

      function yToTime(y) {
        const timelineH = timelineHeight();
        return viewT0 + ((y - H_HEADER) / timelineH) * (viewT1 - viewT0);
      }

      function timeToScrollbarY(t) {
        const timelineH = timelineHeight();
        return H_HEADER + ((t - scenarioStart) / fullDuration) * timelineH;
      }

      function scrollbarYToTime(y) {
        const timelineH = timelineHeight();
        return scenarioStart + ((y - H_HEADER) / timelineH) * fullDuration;
      }

      function formatIsoTime(t) {
        const d = new Date(t * 1000);
        return d.toISOString().substr(11, 8); // HH:MM:SS
      }

      function formatIsoTimeMs(t) {
        const d = new Date(t * 1000);
        return d.toISOString().substr(11, 12); // HH:MM:SS.mmm
      }

      function formatDuration(sec) {
        if (sec >= 1) {
          return sec.toFixed(3) + 's';
        } else {
          return (sec * 1000).toFixed(1) + 'ms';
        }
      }


      function drawTimeScale(timeX, timeWidth) {
        const span = viewT1 - viewT0;
        let tickInterval = 60; // 1 min default
        if (span > 1800) tickInterval = 300; // 5 min
        else if (span > 600) tickInterval = 120; // 2 min
        else if (span > 120) tickInterval = 60; // 1 min
        else if (span > 30) tickInterval = 10; // 10s
        else if (span > 10) tickInterval = 5; // 5s
        else if (span > 2) tickInterval = 1; // 1s
        else if (span > 0.5) tickInterval = 0.1;
        else tickInterval = 0.01;

        const firstTick = Math.ceil(viewT0 / tickInterval) * tickInterval;
        ctx.font = '10px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';

        for (let t = firstTick; t <= viewT1; t += tickInterval) {
          const y = timeToY(t);
          if (y >= H_HEADER && y <= H_HEADER + timelineHeight()) {
            // Horizontal guideline
            ctx.strokeStyle = 'rgba(226, 232, 240, 0.8)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(timeX, y);
            ctx.lineTo(width - W_SCROLLBAR, y);
            ctx.stroke();

            // Tick in time column
            ctx.strokeStyle = '#94a3b8';
            ctx.beginPath();
            ctx.moveTo((timeX + timeWidth) - 5, y);
            ctx.lineTo((timeX + timeWidth), y);
            ctx.stroke();

            // Time label
            const label = tickInterval < 1 ? formatIsoTimeMs(t) : formatIsoTime(t);
            ctx.fillText(label, (timeX + timeWidth) - 7, y);
          }
        }

      }

      function drawScrollbar(markers = []) {
        const sbX = width - W_SCROLLBAR;
        ctx.fillStyle = '#f1f5f9';
        ctx.fillRect(sbX, H_HEADER, W_SCROLLBAR, timelineHeight());

        // Scrollbar thumb
        const thumbY0 = timeToScrollbarY(viewT0);
        const thumbY1 = timeToScrollbarY(viewT1);
        const thumbH = Math.max(8, thumbY1 - thumbY0);

        ctx.fillStyle = 'rgba(59, 130, 246, 0.35)';
        ctx.fillRect(sbX + 2, thumbY0, W_SCROLLBAR - 4, thumbH);
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(sbX + 2, thumbY0, W_SCROLLBAR - 4, thumbH);

        markers.forEach((t) => {
          const sy = timeToScrollbarY(t);
          ctx.strokeStyle = '#d97706';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(sbX, sy);
          ctx.lineTo(sbX + 4, sy);
          ctx.stroke();
        });
      }

      function positionTooltip(e) {
        const rect = container.getBoundingClientRect();
        let posX = e.clientX - rect.left + 15;
        let posY = e.clientY - rect.top + 15;

        if (posX + tooltip.offsetWidth > width) {
          posX = e.clientX - rect.left - tooltip.offsetWidth - 15;
        }
        if (posY + tooltip.offsetHeight > height) {
          posY = e.clientY - rect.top - tooltip.offsetHeight - 15;
        }

        tooltip.style.left = Math.max(5, posX) + 'px';
        tooltip.style.top = Math.max(5, posY) + 'px';
      }
      let clickAnchor = null;
      let dragged = false;

      // Mouse Events
      canvas.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Left click only

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        clickAnchor = {x, y};
        dragged = false;
        tooltip.style.display = 'none';
        if (x >= width - W_SCROLLBAR) {
          // Click on scrollbar
          isDraggingScrollbar = true;
          const targetTime = scrollbarYToTime(y);
          const currentSpan = viewT1 - viewT0;
          viewT0 = targetTime - currentSpan / 2;
          viewT1 = targetTime + currentSpan / 2;
          clampView();
          requestDraw();
        {% if timeline_horizontal %}
        } else if (inHScrollbar(x, y)) {
          isDraggingHScrollbar = true;
          centerLanesOn(hScrollbarXToLane(x));
          requestDraw();
        {% endif %}
        } else {
          // Click on main timeline
          isDraggingMain = true;
          {% if timeline_horizontal %}
          dragAnchorX = x;
          dragStartL0 = viewL0;
          dragStartL1 = viewL1;
          {% endif %}
          dragAnchorY = y;
          dragAnchorTime = yToTime(y);
          dragStartT0 = viewT0;
          dragStartT1 = viewT1;
          dragWithShift = e.shiftKey;
          canvas.style.cursor = 'grabbing';
        }
      });

      window.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (clickAnchor && Math.hypot(x - clickAnchor.x, y - clickAnchor.y) > 4) dragged = true;
        if (isDraggingScrollbar) {
          const targetTime = scrollbarYToTime(y);
          const currentSpan = viewT1 - viewT0;
          viewT0 = targetTime - currentSpan / 2;
          viewT1 = targetTime + currentSpan / 2;
          clampView();
          requestDraw();
          return;
        }

        {% if timeline_horizontal %}
        if (isDraggingHScrollbar) {
          centerLanesOn(hScrollbarXToLane(x));
          requestDraw();
          return;
        }
        {% endif %}

        if (isDraggingMain) {
          if (!dragged) return;
          const timelineH = timelineHeight();
          if (e.shiftKey || dragWithShift) {
            // Shift + Drag: Zoom centered at dragAnchorTime
            // Dragging down (dy > 0) zooms in (smaller span); dragging up (dy < 0) zooms out (larger span)
            const dy = y - dragAnchorY;
            const zoomFactor = Math.exp(-dy * 0.005);
            const span = (dragStartT1 - dragStartT0) * zoomFactor;
            const ratio = (dragAnchorTime - dragStartT0) / (dragStartT1 - dragStartT0);
            viewT0 = dragAnchorTime - span * ratio;
            viewT1 = dragAnchorTime + span * (1 - ratio);
          } else {
            // Left Drag: Pan view (keeping clicked time directly under cursor)
            const dt = ((y - dragAnchorY) / timelineH) * (dragStartT1 - dragStartT0);
            viewT0 = dragStartT0 - dt;
            viewT1 = dragStartT1 - dt;
            {% if timeline_horizontal %}
            const dl = ((x - dragAnchorX) / opsWidth()) * (dragStartL1 - dragStartL0);
            viewL0 = dragStartL0 - dl;
            viewL1 = dragStartL1 - dl;
            clampLanes();
            {% endif %}
          }
          clampView();
          requestDraw();
          return;
        }

        if (x < 0 || x > width || y < H_HEADER || y > height) {
          setHoveredItem(null);
          tooltip.style.display = 'none';
          canvas.style.cursor = 'grab';
          return;
        }
        const item = hitTest(x, y);
        canvas.style.cursor = x >= width - W_SCROLLBAR {% if timeline_horizontal %}|| inHScrollbar(x, y) {% endif %}|| (item && (item.href || item.type === 'op' || item.type === 'event'))
          ? 'pointer' : item && item.type === 'time' ? 'crosshair' : 'grab';
        setHoveredItem(item);
        updateTooltip(e, item);
      });

      canvas.addEventListener('mouseleave', () => {
        setHoveredItem(null);
        tooltip.style.display = 'none';
      });

      window.addEventListener('mouseup', (e) => {
        if (isDraggingMain && !dragged && !dragWithShift && !e.shiftKey && clickAnchor) {
          const rect = canvas.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          if (Math.hypot(x - clickAnchor.x, y - clickAnchor.y) <= 4) {
            const item = hitTest(x, y);
            if (item && item.href) window.location.href = item.href;
          }
        }
        clickAnchor = null;
        isDraggingMain = false;
        isDraggingScrollbar = false;
        {% if timeline_horizontal %}
        isDraggingHScrollbar = false;
        {% endif %}
        canvas.style.cursor = 'grab';
      });

      canvas.addEventListener('wheel', (e) => {
        e.preventDefault();

        const rect = canvas.getBoundingClientRect();
        {% if timeline_horizontal %}
        const x = e.clientX - rect.left;
        {% endif %}
        const y = e.clientY - rect.top;
        const cursorTime = yToTime(y);

        {% if timeline_horizontal %}
        if (e.ctrlKey || e.metaKey || e.altKey) {
          // Ctrl/Cmd/Alt + Wheel (and trackpad pinch, reported as Ctrl + Wheel): zoom lanes centered at cursor
          const delta = e.deltaY !== 0 ? e.deltaY : e.deltaX;
          if (delta === 0) return;
          // Pinch gestures report small deltas, so scale them up to a usable zoom speed
          const scaled = e.ctrlKey && Math.abs(delta) < 10 ? delta * 10 : delta;
          const zoomFactor = Math.max(0.5, Math.min(2.0, Math.exp((scaled / 100) * 0.2)));
          const anchorLane = x >= X_OPS_START ? xToLane(x) : (viewL0 + viewL1) / 2;
          zoomLanesAround(anchorLane, zoomFactor);
          hoveredItem = null;
          tooltip.style.display = 'none';
          requestDraw();
          return;
        }

        if (!e.shiftKey && Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
          // Horizontal wheel / trackpad swipe: scroll lanes left / right
          const span = viewL1 - viewL0;
          const dl = (e.deltaX / opsWidth()) * span;
          viewL0 += dl;
          viewL1 += dl;
          clampLanes();
          hoveredItem = null;
          tooltip.style.display = 'none';
          requestDraw();
          return;
        }

        {% endif %}

        // Normalize delta across platforms where shiftKey may convert deltaY to deltaX
        const delta = e.deltaY !== 0 ? e.deltaY : e.deltaX;
        if (delta === 0) return;

        if (e.shiftKey) {
          // Shift + Wheel: Zoom centered at cursor
          // delta < 0 (scrolling up / forward): zoom IN (factor < 1, span decreases)
          // delta > 0 (scrolling down / backward): zoom OUT (factor > 1, span increases)
          const zoomFactor = Math.max(0.5, Math.min(2.0, Math.exp((delta / 100) * 0.2)));
          const currentSpan = viewT1 - viewT0;
          const newSpan = currentSpan * zoomFactor;

          const ratio = (cursorTime - viewT0) / currentSpan;
          viewT0 = cursorTime - newSpan * ratio;
          viewT1 = cursorTime + newSpan * (1 - ratio);
        } else {
          // Normal Wheel: Scroll view up / down
          const currentSpan = viewT1 - viewT0;
          const dt = (delta / 100) * currentSpan * 0.15;
          viewT0 += dt;
          viewT1 += dt;
        }

        tooltip.style.display = 'none';
        hoveredItem = null;
        clampView();
        requestDraw();
      }, { passive: false });

      // Button controls
      document.getElementById('btn-zoom-in').addEventListener('click', () => {
        const center = (viewT0 + viewT1) / 2;
        const newSpan = (viewT1 - viewT0) * 0.7;
        viewT0 = center - newSpan / 2;
        viewT1 = center + newSpan / 2;
        clampView();
        requestDraw();
      });

      document.getElementById('btn-zoom-out').addEventListener('click', () => {
        const center = (viewT0 + viewT1) / 2;
        const newSpan = (viewT1 - viewT0) * 1.4;
        viewT0 = center - newSpan / 2;
        viewT1 = center + newSpan / 2;
        clampView();
        requestDraw();
      });

      {% if timeline_horizontal %}
      document.getElementById('btn-hzoom-in').addEventListener('click', () => {
        zoomLanesAround((viewL0 + viewL1) / 2, 0.5);
        requestDraw();
      });

      document.getElementById('btn-hzoom-out').addEventListener('click', () => {
        zoomLanesAround((viewL0 + viewL1) / 2, 2.0);
        requestDraw();
      });

      {% endif %}
      document.getElementById('btn-reset-view').addEventListener('click', () => {
        viewT0 = scenarioStart;
        viewT1 = scenarioEnd;
        {% if timeline_horizontal %}
        viewL0 = 0;
        viewL1 = totalLanes;
        {% endif %}
        clampView();
        requestDraw();
      });
