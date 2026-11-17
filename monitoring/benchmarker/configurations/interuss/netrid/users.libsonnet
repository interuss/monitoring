{
  basic_flight_planner: function(dss_pool, uniform_random_spacing=null) {
    flight_generation: {
      independent_time_location_shape: {
        time: {
          fixed_spacing: '0s',
          [if uniform_random_spacing != null then 'uniform_random_spacing']: uniform_random_spacing,
        },
        location: {
          fixed_location: {
            horizontal: {lat: 34, lng: -118},
            vertical: {value: 300, reference: 'W84', units: 'M'},
          },
        },
        shape: {
          fixed_volumes: {
            origin_horizontal: {lat: 0, lng: 0},
            origin_vertical: {value: 0, reference: 'W84', units: 'M'},
            origin_time: '2026-01-01T00:00:00Z',
            volumes: [
              {
                volume: {
                  outline_polygon: {
                    vertices: [
                      {lat: -0.00001, lng: -0.00001},
                      {lat: 0.00001, lng: -0.00001},
                      {lat: 0.00001, lng: 0.00001},
                      {lat: -0.00001, lng: 0.00001},
                    ],
                  },
                  altitude_lower: {value: 0, reference: 'W84', units: 'M'},
                  altitude_upper: {value: 20, reference: 'W84', units: 'M'},
                },
                time_start: '2026-01-01T00:00:00Z',
                time_end: '2026-01-01T00:00:05Z',
              },
            ],
          },
        },
      },
    },
    astm_netrid_behavior: {
      rid_version: 'F3411-22a',
      dss_pool: dss_pool,
      dss_selection_strategy: 'Random',
      isa_strategy: {
        isa_per_flight: {
          before_flight_start: '0s',
          after_flight_end: '2s',
        },
      },
    },
  },
}
