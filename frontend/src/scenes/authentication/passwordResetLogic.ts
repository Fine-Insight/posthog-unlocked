import { kea, path, reducers } from 'kea'
import { loaders } from 'kea-loaders'
import { urlToAction } from 'kea-router'
import { forms } from 'kea-forms'
import api from 'lib/api'
import { lemonToast } from 'lib/lemon-ui/lemonToast'
import type { passwordResetLogicType } from './passwordResetLogicType'
import i18n from 'src/initI18n'
export interface ResponseType {
    success: boolean
    errorCode?: string
    errorDetail?: string
}
export interface ResetResponseType extends ResponseType {
    email?: string
}

export interface ValidatedTokenResponseType extends ResponseType {
    token?: string
    uuid?: string
}

export interface PasswordResetForm {
    password: string
    passwordConfirm: string
}

export const passwordResetLogic = kea<passwordResetLogicType>([
    path(['scenes', 'authentication', 'passwordResetLogic']),
    loaders(({}) => ({
        validatedResetToken: [
            null as ValidatedTokenResponseType | null,
            {
                validateResetToken: async ({ uuid, token }: { uuid: string; token: string }) => {
                    try {
                        await api.get(`api/reset/${uuid}/?token=${token}`)
                        return { success: true, token, uuid }
                    } catch (e: any) {
                        return { success: false, errorCode: e.code, errorDetail: e.detail }
                    }
                },
            },
        ],
    })),
    reducers({
        requestPasswordResetSucceeded: [
            false,
            {
                submitRequestPasswordResetSuccess: () => true,
            },
        ],
        passwordResetSucceeded: [
            false,
            {
                submitPasswordResetSuccess: () => true,
            },
        ],
    }),
    forms(({ values, actions }) => ({
        requestPasswordReset: {
            defaults: {} as unknown as { email: string },
            errors: ({ email }) => ({
                email: !email ? 'Please enter your email to continue' : undefined,
            }),
            submit: async ({ email }, breakpoint) => {
                await breakpoint()

                try {
                    await api.create('api/reset/', { email })
                } catch (e: any) {
                    actions.setRequestPasswordResetManualErrors({ email: e.detail })
                }
            },
        },

        passwordReset: {
            defaults: {} as unknown as PasswordResetForm,
            errors: ({ password, passwordConfirm }) => ({
                password: !password
                    ? i18n.t('common.signup.passwordRoles.02')
                    : password.length < 8
                    ? i18n.t('common.signup.passwordRoles.01')
                    : undefined,
                passwordConfirm: !passwordConfirm
                    ? 'Please confirm your password to continue'
                    : password !== passwordConfirm
                    ? 'Passwords do not match'
                    : undefined,
            }),
            submit: async ({ password }, breakpoint) => {
                await breakpoint(150)

                if (!values.validatedResetToken?.token || !values.validatedResetToken.uuid) {
                    return
                }
                try {
                    await api.create(`api/reset/${values.validatedResetToken.uuid}/`, {
                        password,
                        token: values.validatedResetToken.token,
                    })
                    lemonToast.success('Your password has been changed. Redirecting…')
                    await breakpoint(3000)
                    window.location.href = '/' // We need the refresh
                } catch (e: any) {
                    actions.setPasswordResetManualErrors({ password: e.detail })
                }
            },
        },
    })),
    urlToAction(({ actions }) => ({
        '/reset/:uuid/:token': ({ uuid, token }) => {
            if (token && uuid) {
                actions.validateResetToken({ uuid, token })
            }
        },
    })),
])
