import { useEffect, useMemo, useState } from "react";
import {
  Select, Spin, Tag, Tabs, Space, Empty, Typography,
} from "antd";
import {
  getCropTree, getPopularCrops, type CropDTO,
} from "../services/api";

const { Text } = Typography;

interface Props {
  value?: number | null;
  onChange?: (cropId: number | null, crop: CropDTO | null) => void;
  style?: React.CSSProperties;
  disabled?: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  grain: "粮食作物",
  oil: "油料作物",
  vegetable: "蔬菜",
  fruit: "水果",
  herb: "中药材",
  cash: "经济作物",
  other: "其他",
};

/**
 * 作物选择器，支持：
 *  1. 常用作物快捷按钮
 *  2. 按分类分组 Select，带搜索
 */
export default function CropSelector({
  value, onChange, style, disabled,
}: Props) {
  const [tree, setTree] = useState<Record<string, CropDTO[]>>({});
  const [popular, setPopular] = useState<CropDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"popular" | "all">("popular");

  useEffect(() => {
    (async () => {
      try {
        const [treeRes, popRes] = await Promise.all([getCropTree(), getPopularCrops()]);
        setTree(treeRes.data);
        setPopular(popRes.data);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const allCrops = useMemo(
    () => Object.values(tree).flat() as CropDTO[],
    [tree]
  );

  const options = useMemo(() => {
    return Object.entries(tree).map(([category, crops]) => ({
      label: CATEGORY_LABELS[category] ?? category,
      title: CATEGORY_LABELS[category] ?? category,
      options: crops.map((c) => ({
        value: c.id,
        label: c.name,
        key: `c_${c.id}`,
      })),
    }));
  }, [tree]);

  const handleSelect = (cropId: number | null) => {
    if (cropId === null) {
      onChange?.(null, null);
      return;
    }
    const crop = allCrops.find((c) => c.id === cropId) || null;
    onChange?.(cropId, crop);
  };

  if (loading) {
    return <Spin size="small" />;
  }

  return (
    <div style={style}>
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as "popular" | "all")}
        size="small"
        items={[
          {
            key: "popular",
            label: "常用作物",
            children: popular.length === 0 ? (
              <Empty description="暂无常用作物" />
            ) : (
              <Space wrap size={[8, 8]}>
                {popular.map((c) => (
                  <Tag.CheckableTag
                    key={c.id}
                    checked={value === c.id}
                    onChange={(checked) => handleSelect(checked ? c.id : null)}
                    style={{
                      padding: "4px 12px",
                      fontSize: 13,
                      borderRadius: 16,
                      cursor: disabled ? "not-allowed" : "pointer",
                    }}
                  >
                    {c.name}
                  </Tag.CheckableTag>
                ))}
              </Space>
            ),
          },
          {
            key: "all",
            label: "按分类选择",
            children: (
              <Select
                showSearch
                allowClear
                placeholder="搜索或选择作物"
                value={value ?? undefined}
                onChange={(v) => handleSelect((v as number) ?? null)}
                options={options}
                optionFilterProp="label"
                style={{ width: "100%" }}
                disabled={disabled}
                notFoundContent={<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              />
            ),
          },
        ]}
      />
      {value && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          已选: {allCrops.find((c) => c.id === value)?.name || "未知"}
        </Text>
      )}
    </div>
  );
}
