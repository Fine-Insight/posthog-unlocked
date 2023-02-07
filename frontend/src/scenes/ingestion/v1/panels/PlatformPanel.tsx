import { useActions } from 'kea'
import { ingestionLogic } from 'scenes/ingestion/v1/ingestionLogic'
import { platforms } from 'scenes/ingestion/v1/constants'
import { LemonButton } from 'lib/lemon-ui/LemonButton'
import './Panels.scss'
import { LemonDivider } from 'lib/lemon-ui/LemonDivider'

export function PlatformPanel(): JSX.Element {
    const { setPlatform } = useActions(ingestionLogic)

    return (
        <div>
            <h1 className="ingestion-title">欢迎使用 Authing Insight</h1>
            {/* <p>首先，您想从哪里发送事件？ 您以后可以随时检测更多来源。</p> */}
            <LemonDivider thick dashed className="my-6" />
            <div className="flex flex-col mb-6">
                <LemonButton
                    key={platforms[0]}
                    fullWidth
                    center
                    size="large"
                    type="primary"
                    className="mb-2"
                    onClick={() => setPlatform(platforms[0])}
                >
                    开始
                </LemonButton>

                {/* {platforms.map((platform) => (
                    <LemonButton
                        key={platform}
                        fullWidth
                        center
                        size="large"
                        type="primary"
                        className="mb-2"
                        onClick={() => setPlatform(platform)}
                    >
                        {platform}
                    </LemonButton>
                ))} */}
                {/* <LemonButton
                    onClick={() => setPlatform(THIRD_PARTY)}
                    fullWidth
                    center
                    size="large"
                    className="mb-2"
                    type="primary"
                >
                    {THIRD_PARTY}
                </LemonButton> */}
                {/* <LemonButton type="secondary" size="large" fullWidth center onClick={() => setPlatform(BOOKMARKLET)}>
                    {BOOKMARKLET}
                </LemonButton> */}
            </div>
        </div>
    )
}
