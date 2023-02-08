import { useRef, useEffect } from 'react'
import { LemonInput, LemonButton } from '@posthog/lemon-ui'
import { useValues } from 'kea'
import { Form } from 'kea-forms'
import { Field } from 'lib/forms/Field'
import PasswordStrength from 'lib/components/PasswordStrength'
import { SocialLoginButtons } from 'lib/components/SocialLoginButton'
import { preflightLogic } from 'scenes/PreflightCheck/preflightLogic'
import { signupLogic } from '../signupLogic'
import { Link } from 'lib/lemon-ui/Link'
import { useTranslation } from 'react-i18next'

export function SignupPanel1(): JSX.Element | null {
    const { preflight } = useValues(preflightLogic)
    const { isSignupPanel1Submitting, signupPanel1 } = useValues(signupLogic)
    const emailInputRef = useRef<HTMLInputElement | null>(null)
    const { t } = useTranslation()

    useEffect(() => {
        // There's no password in the demo environment
        emailInputRef?.current?.focus()
    }, [preflight?.demo])

    return (
        <div className="space-y-4 Signup__panel__1">
            {!preflight?.demo && (
                <>
                    <div className="mt-6">
                        <SocialLoginButtons caption="Sign up with" bottomDivider />
                    </div>
                    <p className="text-muted text-center mb-0">{t('common.signup.signupDes')}</p>
                </>
            )}
            <Form logic={signupLogic} formKey={'signupPanel1'} className="space-y-4" enableFormOnSubmit>
                <Field name="email" label={t('common.email')}>
                    <LemonInput
                        className="ph-ignore-input"
                        autoFocus
                        data-attr="signup-email"
                        placeholder="email@yourcompany.com"
                        type="email"
                        ref={emailInputRef}
                        disabled={isSignupPanel1Submitting}
                    />
                </Field>
                {!preflight?.demo && (
                    <Field
                        name="password"
                        label={
                            <div className="flex flex-1 items-center justify-between">
                                <span>{t('common.password')}</span>
                                <span className="w-20">
                                    <PasswordStrength password={signupPanel1.password} />
                                </span>
                            </div>
                        }
                    >
                        <LemonInput
                            type="password"
                            autoComplete="new-password"
                            className="ph-ignore-input"
                            data-attr="password"
                            placeholder="••••••••••"
                            disabled={isSignupPanel1Submitting}
                        />
                    </Field>
                )}
                <LemonButton
                    fullWidth
                    type="primary"
                    center
                    htmlType="submit"
                    data-attr="signup-start"
                    loading={isSignupPanel1Submitting}
                    disabled={isSignupPanel1Submitting}
                >
                    {t('common.continue')}
                </LemonButton>
            </Form>
            {!preflight?.demo && (preflight?.cloud || preflight?.initiated) && (
                // If we're in the demo environment, login is unified with signup and it's passwordless
                // For now, if you're not on Cloud, you wouldn't see this page,
                // but future-proofing this (with `preflight.initiated`) in case this changes
                <div className="text-center mt-4">
                    {t('common.signup.ready')}{' '}
                    <Link to="/login" data-attr="signup-login-link" className="font-bold">
                        {t('common.login')}
                    </Link>
                </div>
            )}
        </div>
    )
}
