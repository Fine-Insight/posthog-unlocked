import './InstructionsPanel.scss'
import { CardContainer } from 'scenes/ingestion/v1/CardContainer'
import {
    AndroidInstructions,
    APIInstructions,
    ElixirInstructions,
    FlutterInstructions,
    GoInstructions,
    IOSInstructions,
    NodeInstructions,
    PHPInstructions,
    PythonInstructions,
    RNInstructions,
    RubyInstructions,
} from 'scenes/ingestion/v1/frameworks'
import { API, MOBILE, BACKEND, WEB } from 'scenes/ingestion/v1/constants'
import { useValues } from 'kea'
import { ingestionLogic } from 'scenes/ingestion/v1/ingestionLogic'
import { WebInstructions } from '../frameworks/WebInstructions'

const frameworksSnippet: Record<string, React.ComponentType> = {
    NODEJS: NodeInstructions,
    GO: GoInstructions,
    RUBY: RubyInstructions,
    PYTHON: PythonInstructions,
    PHP: PHPInstructions,
    ELIXIR: ElixirInstructions,
    ANDROID: AndroidInstructions,
    IOS: IOSInstructions,
    REACT_NATIVE: RNInstructions,
    FLUTTER: FlutterInstructions,
    API: APIInstructions,
}

export function InstructionsPanel(): JSX.Element {
    const { platform, framework, frameworkString } = useValues(ingestionLogic)

    if (platform !== WEB && !framework) {
        return <></>
    }

    const FrameworkSnippet: React.ComponentType = frameworksSnippet[framework as string] as React.ComponentType

    return (
        <div className="InstructionsPanel mb-8">
            {platform === WEB ? (
                <CardContainer showFooter>
                    <WebInstructions />
                </CardContainer>
            ) : framework === API ? (
                <CardContainer showFooter>
                    <h2>{frameworkString}</h2>
                    <p className="prompt-text">
                        {'下面是使用我们提供的 API 捕获事件的简单格式。 使用此端点发送您的第一个事件！'}
                    </p>
                    <FrameworkSnippet />
                </CardContainer>
            ) : (
                <CardContainer showFooter>
                    <h1>{`Setup ${frameworkString}`}</h1>

                    {platform === BACKEND ? (
                        <>
                            <p className="prompt-text">
                                {`按照以下说明从您的网站发送自定义事件 ${frameworkString} 后端.`}
                            </p>
                            <FrameworkSnippet />
                        </>
                    ) : null}
                    {platform === MOBILE ? <FrameworkSnippet /> : null}
                </CardContainer>
            )}
        </div>
    )
}
