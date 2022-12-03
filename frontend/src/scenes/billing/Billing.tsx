import { PageHeader } from 'lib/components/PageHeader'
import { Plan } from './Plan'
import { CurrentUsage } from './CurrentUsage'
import { BillingEnrollment } from './BillingEnrollment'
import './Billing.scss'
import { billingLogic } from './billingLogic'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { FEATURE_FLAGS } from 'lib/constants'
import { SceneExport } from 'scenes/sceneTypes'
import { LemonButton, LemonDivider } from '@posthog/lemon-ui'
import { AlertMessage } from 'lib/components/AlertMessage'
import { useValues } from 'kea'
import { BillingV2 } from './v2/control/Billing'
import { BillingV2 as BillingV2Test } from './v2/test/Billing'
import { SpinnerOverlay } from 'lib/components/Spinner/Spinner'

export const scene: SceneExport = {
    component: Billing,
    logic: billingLogic,
}

export function Billing(): JSX.Element {
    const { billing, isSmallScreen, billingVersion } = useValues(billingLogic)
    const { featureFlags } = useValues(featureFlagLogic)

    if (!billingVersion) {
        return <SpinnerOverlay />
    }

    if (billingVersion === 'v2') {
        return (
            <div>
                <PageHeader title="Billing &amp; usage" />
                {featureFlags[FEATURE_FLAGS.BILLING_FEATURES_EXPERIMENT] === 'test' ? <BillingV2Test /> : <BillingV2 />}
            </div>
        )
    }

    return (
        <div className="flex flex-col space-y-6">
            <PageHeader title="Billing &amp; usage" />
            <LemonDivider />
            {billing?.should_setup_billing && (
                <AlertMessage
                    type="warning"
                    action={{
                        children: billing.subscription_url ? (
                            <a href={billing.subscription_url}>
                                <LemonButton>Finish setup</LemonButton>
                            </a>
                        ) : undefined,
                    }}
                >
                    Your plan is <b>currently inactive</b> as you haven't finished setting up your billing information.
                </AlertMessage>
            )}
            {isSmallScreen ? (
                <div className="flex flex-col space-y-4">
                    <CurrentUsage />
                    {billing?.plan ? <Plan plan={billing.plan} currentPlan /> : <BillingEnrollment />}
                </div>
            ) : (
                <div className="flex flex-row space-x-4">
                    <div className="w-2/3">
                        <CurrentUsage />
                    </div>
                    <div className="w-1/3">
                        {billing?.plan && !billing?.should_setup_billing ? (
                            <Plan plan={billing.plan} currentPlan />
                        ) : (
                            <BillingEnrollment />
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
