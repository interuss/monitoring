local s2_latlng_rect_part = std.native('s2.latlng_rect_part');

{
  laglng_rect_location: function(rect) {
    random_location: {
      uniform_box: {
        lat_min: s2_latlng_rect_part(rect, 'lat_lo'),
        lat_max: s2_latlng_rect_part(rect, 'lat_hi'),
        lng_min: s2_latlng_rect_part(rect, 'lng_lo'),
        lng_max: s2_latlng_rect_part(rect, 'lng_hi'),
      },
      vertical: {value: 300, reference: 'W84', units: 'M'},
    },
  },

  latlng_rect_shape: function(lat_size, lng_size) {
    fixed_volumes: {
      origin_horizontal: {lat: 0, lng: 0},
      origin_vertical: {value: 0, reference: 'W84', units: 'M'},
      origin_time: '2026-01-01T00:00:00Z',
      volumes: [
        {
          volume: {
            outline_polygon: {
              vertices: [
                {lat: -lat_size, lng: -lng_size},
                {lat: lat_size, lng: -lng_size},
                {lat: lat_size, lng: lng_size},
                {lat: -lat_size, lng: lng_size},
              ],
            },
            altitude_lower: {value: 0, reference: 'W84', units: 'M'},
            altitude_upper: {value: 20, reference: 'W84', units: 'M'},
          },
          time_start: '2026-01-01T00:00:00Z',
          time_end: '2026-01-01T00:00:15Z',
        },
      ],
    },
  },
}
