import { Button, Col, Row, Space } from 'antd'
import './TableConfig.scss'
import { useActions, useValues } from 'kea'
import { tableConfigLogic } from './tableConfigLogic'
import Modal from 'antd/lib/modal/Modal'
import VirtualizedList, { ListRowProps } from 'react-virtualized/dist/es/List'
import { AutoSizer } from 'react-virtualized/dist/es/AutoSizer'
import { PropertyKeyInfo } from '../PropertyKeyInfo'
import clsx from 'clsx'
import { columnConfiguratorLogic } from 'lib/components/ResizableTable/columnConfiguratorLogic'
import { TaxonomicFilter } from 'lib/components/TaxonomicFilter/TaxonomicFilter'
import { TaxonomicFilterGroupType } from 'lib/components/TaxonomicFilter/types'
import { LemonButton } from 'lib/lemon-ui/LemonButton'
import { IconClose, IconLock, IconTuning, SortableDragIcon } from 'lib/lemon-ui/icons'
import { LemonCheckbox } from 'lib/lemon-ui/LemonCheckbox'
import {
    SortableContainer as sortableContainer,
    SortableElement as sortableElement,
    SortableHandle as sortableHandle,
} from 'react-sortable-hoc'
import { RestrictedArea, RestrictedComponentProps, RestrictionScope } from '../RestrictedArea'
import { TeamMembershipLevel } from 'lib/constants'

const DragHandle = sortableHandle(() => (
    <span className="drag-handle">
        <SortableDragIcon />
    </span>
))

interface TableConfigProps {
    immutableColumns?: string[] //the titles of the columns that are always displayed
    defaultColumns: string[] // the keys of the set of columns to show when there is no user choice
}

export function LemonTableConfig(props: TableConfigProps): JSX.Element {
    const { showModal } = useActions(tableConfigLogic)

    return (
        <>
            <LemonButton
                type="secondary"
                data-attr="events-table-column-selector"
                onClick={showModal}
                icon={<IconTuning style={{ color: 'var(--primary)' }} />}
            >
                Configure columns
            </LemonButton>
            <ColumnConfigurator immutableColumns={props.immutableColumns} defaultColumns={props.defaultColumns} />
        </>
    )
}

function ColumnConfigurator({ immutableColumns, defaultColumns }: TableConfigProps): JSX.Element {
    // the virtualised list doesn't support gaps between items in the list
    // setting the container to be larger than we need
    // and adding a container with a smaller height to each row item
    // allows the new row item to set a margin around itself
    const rowContainerHeight = 36
    const rowItemHeight = 32

    const { selectedColumns: currentlySelectedColumns, modalVisible } = useValues(tableConfigLogic)
    const { hideModal } = useActions(tableConfigLogic)

    const configuratorLogic = columnConfiguratorLogic({
        selectedColumns: currentlySelectedColumns === 'DEFAULT' ? defaultColumns : currentlySelectedColumns,
    })
    const { selectColumn, unselectColumn, resetColumns, setColumns, toggleSaveAsDefault, save } =
        useActions(configuratorLogic)
    const { selectedColumns } = useValues(configuratorLogic)

    function SaveColumnsAsDefault({ isRestricted }: RestrictedComponentProps): JSX.Element {
        return (
            <LemonCheckbox
                label="Save as default for all project members"
                className="mt-2"
                data-attr="events-table-save-columns-as-default-toggle"
                bordered
                onChange={toggleSaveAsDefault}
                defaultChecked={false}
                disabled={isRestricted}
            />
        )
    }
    const SelectedColumn = ({ column, disabled }: { column: string; disabled?: boolean }): JSX.Element => {
        return (
            <div
                className={clsx(['column-display-item', { selected: !disabled, disabled: disabled }])}
                /* eslint-disable-next-line react/forbid-dom-props */
                style={{ height: rowItemHeight }}
            >
                <div className="flex items-center">
                    {!disabled && <DragHandle />}
                    <PropertyKeyInfo
                        value={
                            column.startsWith('properties.')
                                ? column.substring(11)
                                : column.startsWith('person.properties.')
                                ? column.substring(18)
                                : column
                        }
                    />
                </div>
                <LemonButton
                    data-attr="column-display-item-remove-icon"
                    onClick={() => unselectColumn(column)}
                    status={!disabled ? 'danger' : 'muted'}
                    size="small"
                    icon={disabled ? <IconLock /> : <IconClose />}
                    disabledReason={disabled && "This column can't be removed because it's essential."}
                    tooltip={!disabled && 'Remove this column.'}
                />
            </div>
        )
    }

    const SortableSelectedColumn = sortableElement(SelectedColumn)

    const SortableSelectedColumnRenderer = ({ index, style, key }: ListRowProps): JSX.Element => {
        const disabled = immutableColumns?.includes(selectedColumns[index])
        return (
            <div style={style} key={key}>
                {disabled && <SelectedColumn column={selectedColumns[index]} disabled={Boolean(disabled)} />}
                {!disabled && (
                    <SortableSelectedColumn
                        column={selectedColumns[index]}
                        index={index}
                        collection="selected-columns"
                    />
                )}
            </div>
        )
    }

    const SortableColumnList = sortableContainer(() => (
        <div style={{ height: 320 }} className="selected-columns-col">
            <AutoSizer>
                {({ height, width }: { height: number; width: number }) => {
                    return (
                        <VirtualizedList
                            height={height}
                            rowCount={selectedColumns.length}
                            rowRenderer={SortableSelectedColumnRenderer}
                            rowHeight={rowContainerHeight}
                            width={width}
                        />
                    )
                }}
            </AutoSizer>
        </div>
    ))

    const handleSort = ({ oldIndex, newIndex }: { oldIndex: number; newIndex: number }): void => {
        const newColumns = [...selectedColumns]
        const [removed] = newColumns.splice(oldIndex, 1)
        newColumns.splice(newIndex, 0, removed)
        setColumns(newColumns)
    }

    return (
        <Modal
            id="column-configurator-modal"
            centered
            visible={modalVisible}
            title="Configure columns"
            onOk={save}
            width={700}
            bodyStyle={{ padding: '16px 16px 0 16px' }}
            className="column-configurator-modal"
            okButtonProps={{
                // @ts-expect-error
                'data-attr': 'items-selector-confirm',
            }}
            okText="Save"
            onCancel={hideModal}
            footer={
                <Row>
                    <Space style={{ flexGrow: 1 }} align="start">
                        <Button className="text-blue" onClick={() => resetColumns(defaultColumns)}>
                            Reset to defaults
                        </Button>
                    </Space>
                    <Space>
                        <Button className="text-blue" type="text" onClick={hideModal}>
                            Close
                        </Button>
                        <Button type="primary" onClick={save}>
                            Save
                        </Button>
                    </Space>
                </Row>
            }
        >
            <div className="main-content">
                <Row gutter={16} className="lists">
                    <Col xs={24} sm={12}>
                        <h4 className="secondary uppercase text-muted">
                            Visible columns ({selectedColumns.length}) - Drag to reorder
                        </h4>
                        <SortableColumnList
                            helperClass="column-configurator-modal-sortable-container"
                            onSortEnd={handleSort}
                            distance={5}
                            useDragHandle
                            lockAxis="y"
                        />
                    </Col>
                    <Col xs={24} sm={12}>
                        <h4 className="secondary uppercase text-muted">Available columns</h4>
                        <div style={{ height: 320 }}>
                            <AutoSizer>
                                {({ height, width }: { height: number; width: number }) => {
                                    return (
                                        <TaxonomicFilter
                                            height={height}
                                            width={width}
                                            taxonomicGroupTypes={[
                                                TaxonomicFilterGroupType.EventProperties,
                                                TaxonomicFilterGroupType.EventFeatureFlags,
                                            ]}
                                            value={undefined}
                                            onChange={(_, value) => value && selectColumn(String(value))}
                                            popoverEnabled={false}
                                            selectFirstItem={false}
                                            excludedProperties={{
                                                [TaxonomicFilterGroupType.EventProperties]: selectedColumns,
                                                [TaxonomicFilterGroupType.EventFeatureFlags]: selectedColumns,
                                            }}
                                        />
                                    )
                                }}
                            </AutoSizer>
                        </div>
                    </Col>
                </Row>
                <RestrictedArea
                    Component={SaveColumnsAsDefault}
                    minimumAccessLevel={TeamMembershipLevel.Admin}
                    scope={RestrictionScope.Project}
                />
            </div>
        </Modal>
    )
}
