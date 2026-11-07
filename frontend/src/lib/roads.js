// A crash's road fields as one line, then where a house-address crash happened (#397: "in front of 440 W MANCHESTER
// BLVD"). empty: what a missing field shows.
export function roadsText(c, empty = '') {
  const roads = `${c.primary_road || empty} / ${c.secondary_road || empty}`
  return c.location_label ? `${roads} (${c.location_label})` : roads
}
