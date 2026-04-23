export type ScryfallImageSize = 'small' | 'normal' | 'large'
export type ScryfallFace = 'front' | 'back'

export const CARD_BACK_URL =
  'https://cards.scryfall.io/small/back/0/0/0aeebaf5-8c7d-4636-9e82-8c27447861f7.jpg'

export function scryfallImageUrl(
  scryfallId: string,
  face: ScryfallFace = 'front',
  size: ScryfallImageSize = 'small'
): string {
  return `/card/image/${scryfallId}?size=${size}&face=${face}`
}
