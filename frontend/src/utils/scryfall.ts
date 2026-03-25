export type ScryfallImageSize = 'small' | 'normal' | 'large'
export type ScryfallFace = 'front' | 'back'

export const CARD_BACK_URL =
  'https://cards.scryfall.io/small/back/0/0/0aeebaf5-8c7d-4636-9e82-8c27447861f7.jpg'

export function scryfallImageUrl(
  scryfallId: string,
  face: ScryfallFace = 'front',
  size: ScryfallImageSize = 'small'
): string {
  const a = scryfallId[0]
  const b = scryfallId[1]
  return `https://cards.scryfall.io/${size}/${face}/${a}/${b}/${scryfallId}.jpg`
}
