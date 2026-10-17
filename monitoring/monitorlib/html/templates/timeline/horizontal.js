{# Optional horizontal lane viewport; the caller supplies X_OPS_START and data.total_operation_lanes. #}
      // Visible lane window [viewL0, viewL1], in lane units across all origins
      const totalLanes = Math.max(1, data.total_operation_lanes);
      const minLaneSpan = Math.min(1, totalLanes);
      let viewL0 = 0;
      let viewL1 = totalLanes;

      let isDraggingHScrollbar = false;
      let dragAnchorX = 0;
      let dragStartL0 = 0;
      let dragStartL1 = 0;

      function clampLanes() {
        let span = viewL1 - viewL0;
        if (span >= totalLanes) {
          viewL0 = 0;
          viewL1 = totalLanes;
          return;
        }
        if (span < minLaneSpan) {
          const center = (viewL0 + viewL1) / 2;
          span = minLaneSpan;
          viewL0 = center - span / 2;
          viewL1 = center + span / 2;
        }
        if (viewL0 < 0) {
          viewL0 = 0;
          viewL1 = span;
        }
        if (viewL1 > totalLanes) {
          viewL1 = totalLanes;
          viewL0 = totalLanes - span;
        }
      }

      function zoomLanesAround(lane, factor) {
        const span = viewL1 - viewL0;
        const newSpan = span * factor;
        const ratio = (lane - viewL0) / span;
        viewL0 = lane - newSpan * ratio;
        viewL1 = lane + newSpan * (1 - ratio);
        clampLanes();
      }

      function opsWidth() {
        return Math.max(10, width - X_OPS_START - W_SCROLLBAR);
      }

      function laneWidth() {
        return opsWidth() / (viewL1 - viewL0);
      }

      function laneToX(lane) {
        return X_OPS_START + (lane - viewL0) * laneWidth();
      }

      function xToLane(x) {
        return viewL0 + (x - X_OPS_START) / laneWidth();
      }

      function hScrollbarXToLane(x) {
        return ((x - X_OPS_START) / opsWidth()) * totalLanes;
      }

      function inHScrollbar(x, y) {
        return y >= H_HEADER + timelineHeight() && x >= X_OPS_START && x < width - W_SCROLLBAR;
      }

      function centerLanesOn(lane) {
        const span = viewL1 - viewL0;
        viewL0 = lane - span / 2;
        viewL1 = lane + span / 2;
        clampLanes();
      }

      function drawHorizontalScrollbar() {
        const xOpsStart = X_OPS_START;
        const xOpsEnd = width - W_SCROLLBAR;
        const wOpsAvailable = opsWidth();
        const yBottom = H_HEADER + timelineHeight();
        // 8. Horizontal Scroll Bar (Bottom of the operations area)
        ctx.fillStyle = '#f1f5f9';
        ctx.fillRect(xOpsStart, yBottom, wOpsAvailable, H_HSCROLLBAR);
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(xOpsStart, yBottom);
        ctx.lineTo(xOpsEnd, yBottom);
        ctx.stroke();

        const thumbX0 = xOpsStart + (viewL0 / totalLanes) * wOpsAvailable;
        const thumbW = Math.max(8, ((viewL1 - viewL0) / totalLanes) * wOpsAvailable);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.35)';
        ctx.fillRect(thumbX0, yBottom + 2, thumbW, H_HSCROLLBAR - 4);
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(thumbX0, yBottom + 2, thumbW, H_HSCROLLBAR - 4);
      }
