# M1.3 证据｜m1g-20261024T113913Z-platform

日期：2026-10-24。该 release 在服务器以 **18953**（PID 497279）运行，真实地图根目录为 `/home/liaozhengyan/Desktop/mobileCar/var/maps`，Route SQLite 为独立的 `report/m1g-live.sqlite3`。这是资源/显示切片候选，不是 8792 部署、SLAM、导航执行、真实 prepared/Start、运动、录制或 M1 验收。

## 冻结身份

| 项目 | 值 |
|---|---|
| release | `m1g-20261024T113913Z-platform` |
| backend source files | 50 个非缓存文件 |
| source listing SHA-256 | `353a03176994a05c0047913aca03454bdde38c53659a30d9b46802e2b00866bd` |
| native 8792 | PID 941842，drvfix/G4A2；只读观察，未停止或修改 |
| 18949 | M1.2d 生产 recipe 候选，保留运行 |
| frontend | 最新 404c1fc；当前预览 18950 → 18944 |

## 文件

- `platform/openapi.json`：18953 实时 OpenAPI。`WaypointInput.required` 包含 `yaw_rad`，类型为 number。
- `platform/maps.json`、`platform/map-room-a.json`、`platform/map-room-b.json`：真实 G3B Room A/B 固定版本列表/详情，含 id/version/frame、origin、resolution、阈值、资产摘要和 G1 不兼容状态。
- `platform/map-room-a.pgm`：经 HTTP 固定摘要读取的 Room A 显示资产；本地 SHA-256 应与 API `image.sha256` 一致。
- `platform/route-evidence.json`：真实 create、publish v1、save v2、409、fixed reads、missing/null yaw、wrong map/frame、out-of-bounds/occupied/unknown、image mismatch 与 same-content no-op。
- `platform/native-snapshot-before.json`、`platform/native-snapshot-after.json`、`platform/native-comparison.json`：8792 只读 GET 的前后状态；run/generation/episode、owner、recording IDLE、safety latched true 不变。
- `platform/focused-m1g.junit.xml`：M1 相关聚焦 **104 passed**。
- `platform/full-m1g.junit.xml`：平台全量 **108 passed / 3 failed**。3 项是既有 catalog/migrate 外部源码/native docs 布局失败，未跳过或改绿。
- `platform/source-listing-m1g.txt`：服务器 release 的文件哈希清单；工作树同路径列表 hash 一致。
- `platform/gateway-job.json`：候选进程、端口和外部 map/root/db 配置。
- `maps/room_a/`、`maps/room_b/`：真实历史包的 `manifest.json`、`manifest.sha256`、`map.yaml`、`map.pgm`。大体积 posegraph 未复制，只在 API 中给出并核验声明摘要。

## 完整性说明

Room A/B 的实际 `manifest.json` SHA-256 分别为 `aaee7586…6fd34`、`a6e641a5…382c`；包内 `manifest.sha256` 文件分别记录 `ed1cf6ee…ab3f`、`73c549d4…c517`，两者不匹配。服务固定的是实际 manifest，不采用 stale self-check；该 native packaging 缺口保留为未核验项，不伪装成已通过。

Route 样本：`route-9e55257fc5d24a03a54986d9fcaa8a80`；v1 `a9ee5895…84e62`，v2 `370d2462…aa7871c`。重排保留 wp-a/wp-b ID，v1 在 v2 发布后仍字节不变。

## 复现读取

```bash
curl http://127.0.0.1:18953/api/v1/maps
curl http://127.0.0.1:18953/api/v1/maps/map_room_a_g3b_release_v1/versions/v1
curl http://127.0.0.1:18953/api/v1/routes/route-9e55257fc5d24a03a54986d9fcaa8a80/versions/v1
curl http://127.0.0.1:18953/openapi.json
```

只执行 GET；不要调用 start/begin/stop 或其他 native 写端点。
