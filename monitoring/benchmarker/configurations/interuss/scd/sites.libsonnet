local s2_offset_cell = std.native('s2.offset_cell');
local s2_inscribed_latlng_rect = std.native('s2.inscribed_latlng_rect');

{
  /* Generate operating rectangles on a grid of S2 cells at the origin cell's level.
   * spacing_cells > 1 leaves unused cells between sites.  The rectangles are strictly
   * inside their cells so subscriptions at different sites do not overlap.
   */
  grid: function(origin_cell, num_sites, columns, spacing_cells) [
    s2_inscribed_latlng_rect(s2_offset_cell(
      origin_cell,
      (i % columns) * spacing_cells,
      std.floor(i / columns) * spacing_cells,
    )) for i in std.range(0, num_sites - 1)
  ],
}
