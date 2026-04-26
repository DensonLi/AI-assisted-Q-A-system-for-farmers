import { useEffect, useState } from "react";
import { Cascader, Spin, message } from "antd";
import type { DefaultOptionType } from "antd/es/cascader";
import {
  listProvinces, listRegionChildren, getRegion, type RegionDTO,
} from "../services/api";

interface Option extends DefaultOptionType {
  value: number;
  label: string;
  agro_zone?: string | null;
  level: number;
  isLeaf?: boolean;
  loading?: boolean;
  children?: Option[];
}

interface Props {
  value?: number | null;
  onChange?: (regionId: number | null, region: RegionDTO | null) => void;
  placeholder?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
}

function regionToOption(r: RegionDTO): Option {
  return {
    value: r.id,
    label: r.name,
    agro_zone: r.agro_zone,
    level: r.level,
    isLeaf: r.level === 3,
  };
}

/**
 * 3 级区域级联选择器（省 → 市 → 县区）。
 * 采用懒加载：只在展开某节点时才请求其 children。
 */
export default function RegionSelector({
  value, onChange, placeholder = "请选择省/市/县", style, disabled,
}: Props) {
  const [options, setOptions] = useState<Option[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPath, setSelectedPath] = useState<number[] | undefined>(undefined);

  // 初次加载省级
  useEffect(() => {
    (async () => {
      try {
        const { data } = await listProvinces();
        setOptions(data.map(regionToOption));
      } catch {
        message.error("加载省份失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // 根据 value 反向还原级联路径
  useEffect(() => {
    if (!value) { setSelectedPath(undefined); return; }
    (async () => {
      try {
        const { data: current } = await getRegion(value);
        if (!current?.id) return;
        const path: number[] = [current.id];
        let cur = current;
        while (cur.parent_id) {
          const { data: parent } = await getRegion(cur.parent_id);
          if (!parent?.id) break;
          path.unshift(parent.id);
          cur = parent;
        }
        setSelectedPath(path);
        // 确保 options 中已经加载了整条路径的 children
        await ensurePathLoaded(path);
      } catch {
        // 容错
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const ensurePathLoaded = async (path: number[]) => {
    let pointer: Option[] = options;
    for (let i = 0; i < path.length - 1; i++) {
      const id = path[i];
      const node = pointer.find((o) => o.value === id);
      if (!node) return;
      if (!node.children || node.children.length === 0) {
        try {
          const { data: children } = await listRegionChildren(id);
          node.children = children.map(regionToOption);
          setOptions([...options]);
        } catch { /* ignore */ }
      }
      pointer = node.children || [];
    }
  };

  const loadData = async (selectedOptions: Option[]) => {
    const target = selectedOptions[selectedOptions.length - 1];
    target.loading = true;
    try {
      const { data: children } = await listRegionChildren(target.value);
      target.children = children.map(regionToOption);
      if (target.children.length === 0) target.isLeaf = true;
    } catch {
      message.error("加载下级区域失败");
    } finally {
      target.loading = false;
      setOptions([...options]);
    }
  };

  const handleChange = async (path: (string | number)[] | undefined, selected: Option[]) => {
    if (!path || path.length === 0) {
      setSelectedPath(undefined);
      onChange?.(null, null);
      return;
    }
    const leaf = selected[selected.length - 1];
    setSelectedPath(path as number[]);
    try {
      const { data: region } = await getRegion(Number(leaf.value));
      onChange?.(Number(leaf.value), region);
    } catch {
      onChange?.(Number(leaf.value), null);
    }
  };

  if (loading) {
    return <Spin size="small" />;
  }

  return (
    <Cascader
      options={options}
      value={selectedPath}
      loadData={loadData as any}
      onChange={handleChange as any}
      placeholder={placeholder}
      changeOnSelect={false}
      style={{ width: "100%", ...style }}
      disabled={disabled}
      showSearch={{
        filter: (inputValue, path) =>
          path.some((o) => (o.label as string).includes(inputValue)),
      }}
    />
  );
}
