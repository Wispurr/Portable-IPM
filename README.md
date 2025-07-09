# IPM System

## Plan Motivation

Portable vehicles such as bicycles, scooters, and delivery robots are increasingly popular for last-mile transportation due to their convenience and environmental friendliness. However, their small size and limited onboard sensing capabilities often pose challenges for safe navigation, especially in complex urban environments. Traditional camera views are affected by perspective distortion, making it harder for onboard systems or remote operators to accurately perceive distances, object sizes, and spatial relationships on the ground.

Inverse Perspective Mapping (IPM) transforms the camera view into a top-down bird’s-eye perspective, removing perspective distortion and providing a more intuitive, metric-accurate layout of the surrounding environment. This improves obstacle detection, path planning, and overall situational awareness, which is critical for avoiding collisions and ensuring safety.

## Plan Purpose

The purpose of developing an IPM system for portable vehicles is to enhance their perception and navigation capabilities by:

-   Providing a real-time, distortion-free bird’s-eye view of the surrounding area.
-   Improving the accuracy of detecting obstacles, pedestrians, vehicles, and road features.
-   Enabling better path planning and collision avoidance in crowded or narrow spaces.
-   Supporting remote monitoring or autonomous control by delivering intuitive visual information.
-   Enhancing the overall safety and efficiency of portable vehicles during urban travel.

## Repo File Framework

```
Portable-IPM/
├── .gitignore
├── LICENSE
├── README.md
├── backend/                  # Group 3: FastAPI 後端
│   ├── .gitignore
│   ├── README.md
│   ├── app.py
│   ├── requirements.txt
│   ├── static/
│   ├── templates/
│   │   ├── exceptions.html
│   │   └── index.html
│   └── utils/
│       ├── __init__.py
│       ├── api_formatter.py
│       ├── config.py
│       ├── exception_handler.py
│       └── json.py
├── data_samples/             # 偵測用的資料範例與圖片
├── docs/                     # Group 4: 文件與簡報資料
│   └── WBS.md
├── frontend/                 # Group 1: Flutter 專案
├── integration_testing/      # 整合測試與 bug 修正紀錄
└── vision_processing/        # Group 2: IPM 與影像處理模組

```
