import { lemonToast } from '@posthog/lemon-ui'
import { kea, path, connect } from 'kea'
import { forms } from 'kea-forms'
import api from 'lib/api'
import { userLogic } from 'scenes/userLogic'

import type { changePasswordLogicType } from './changePasswordLogicType'
import i18n from 'src/initI18n'
export interface ChangePasswordForm {
    current_password: string
    password: string
}

export const changePasswordLogic = kea<changePasswordLogicType>([
    path(['scenes', 'me', 'settings', 'changePasswordLogic']),
    connect({
        values: [userLogic, ['user']],
    }),
    forms(({ values, actions }) => ({
        changePassword: {
            defaults: {} as unknown as ChangePasswordForm,
            errors: ({ current_password, password }) => ({
                current_password:
                    (!values.user || values.user.has_password) && !current_password
                        ? 'Please enter your current password'
                        : undefined,
                password: !password
                    ? i18n.t('common.signup.passwordRoles.02')
                    : password.length < 8
                    ? i18n.t('common.signup.passwordRoles.01')
                    : undefined,
            }),
            submit: async ({ password, current_password }, breakpoint) => {
                await breakpoint(150)

                try {
                    await api.update('api/users/@me/', {
                        current_password,
                        password,
                    })
                    actions.resetChangePassword({ password: '', current_password: '' })
                    lemonToast.success('Password changed')
                } catch (e: any) {
                    actions.setChangePasswordManualErrors({ [e.attr]: e.detail })
                }
            },
        },
    })),
])
