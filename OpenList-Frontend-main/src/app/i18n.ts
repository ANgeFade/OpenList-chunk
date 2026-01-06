import * as i18n from "@solid-primitives/i18n"
import { createResource, createSignal } from "solid-js"
// Hardcode: Static import of Chinese dictionary
import { dict as zhCNDict } from "~/lang/zh-CN/entry"

export { i18n }

// glob search by Vite
const langs = import.meta.glob("~/lang/*/index.json", {
  eager: true,
  import: "lang",
})

// all available languages
export const languages = Object.keys(langs).map((langPath) => {
  const parts = langPath.split("/")
  const langCode = parts[parts.length - 2]
  const langName = langs[langPath] as string
  return { code: langCode, lang: langName }
})

// Hardcode: Force default language to zh-CN
const defaultLang = "zh-CN"

// Hardcode: Ignore localStorage and ALWAYS use zh-CN
export let initialLang = defaultLang

// if (!languages.some((lang) => lang.code === initialLang)) {
//   initialLang = defaultLang
// }

// Type imports
import type * as en from "~/lang/en/entry"

export type Lang = keyof typeof langs
export type RawDictionary = typeof en.dict
export type Dictionary = i18n.Flatten<RawDictionary>

// Fetch and flatten the dictionary
const fetchDictionary = async (locale: Lang): Promise<Dictionary> => {
  // Hardcode: Return static Chinese dictionary directly if locale is zh-CN or as fallback
  if (locale === "zh-CN") {
    return i18n.flatten(zhCNDict as RawDictionary)
  }
  try {
    const dict: RawDictionary = (await import(`~/lang/${locale}/entry.ts`)).dict
    return i18n.flatten(dict)
  } catch (err) {
    console.error(`Error loading dictionary for locale: ${locale}`, err)
    // Hardcode: Fallback to Chinese on error
    return i18n.flatten(zhCNDict as RawDictionary)
  }
}

// Signals to track current language and dictionary state
export const [currentLang, setCurrentLang] = createSignal<Lang>(initialLang)

export const [dict] = createResource(currentLang, fetchDictionary)
