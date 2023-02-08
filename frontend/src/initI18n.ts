import i18n from 'i18next'
import jsCookie from 'js-cookie'
import { initReactI18next } from 'react-i18next'

import * as enUsTrans from './locales/en'
import * as zhCnTrans from './locales/zh'

export const COOKIE_KEY = '_authing_lang'

export enum Lang {
    zhCn = 'zh-CN',
    enUs = 'en-US',
}
export const LANGS = Object.values(Lang)

const resources = {
    [Lang.enUs]: {
        translation: enUsTrans,
    },
    [Lang.zhCn]: {
        translation: zhCnTrans,
    },
}

export function getInitLang(): any {
    const cookieLang = jsCookie.get(COOKIE_KEY) as Lang
    if (cookieLang) {
        return cookieLang
    }
    const computerLang = navigator.language
    const matched = LANGS.find((item) => item.toLocaleLowerCase().includes(computerLang))
    return matched || Lang.zhCn
}

export function changeLang(lang: Lang): void {
    const topLevelDomain = window.location.hostname.split('.').slice(-2).join('.')
    jsCookie.set(COOKIE_KEY, lang, {
        domain: topLevelDomain,
        path: '/',
    })
    window.location.reload()
}

export function initI18n(): void {
    i18n.use(initReactI18next).init({
        fallbackLng: Lang.zhCn,
        resources: resources,
        debug: false,
        interpolation: {
            escapeValue: false,
        },
    })
    i18n.changeLanguage(getInitLang())
}
