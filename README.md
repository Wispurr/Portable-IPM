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

-   Ver 2.0

```
.
├── LICENSE
├── README.md
├── app.py
├── backend
│   ├── README.md
│   ├── __pycache__
│   │   ├── app.cpython-312.pyc
│   │   ├── config.cpython-312.pyc
│   │   └── main.cpython-312.pyc
│   ├── api
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── shared_camera_manager.py
│   │   └── stream_service.py
│   ├── app.py
│   ├── config.json
│   ├── js
│   ├── package.cmd
│   ├── static
│   ├── templates
│   │   ├── analyze_image.html
│   │   ├── exceptions.html
│   │   ├── index.html
│   │   └── ws_doc.html
│   ├── uploads
│   └── utils
│       ├── __init__.py
│       ├── __pycache__
│       ├── config.json
│       ├── config.py
│       ├── exception_handler.py
│       ├── json.py
│       └── vision_processing
├── config.json
├── docs
│   └── WBS.md
├── frontend
│   ├── README.md
│   ├── analysis_options.yaml
│   ├── android
│   │   ├── app
│   │   ├── build
│   │   ├── build.gradle.kts
│   │   ├── gradle
│   │   ├── gradle.properties
│   │   ├── local.properties
│   │   └── settings.gradle.kts
│   ├── build
│   │   ├── 752c4392497756140c7f3a991c47851a
│   │   ├── b9dbe592fc2ae558329e0a126bb30b5a.cache.dill.track.dill
│   │   ├── flutter_assets
│   │   ├── native_assets
│   │   └── windows
│   ├── ios
│   │   ├── Flutter
│   │   ├── Runner
│   │   ├── Runner.xcodeproj
│   │   ├── Runner.xcworkspace
│   │   └── RunnerTests
│   ├── lib
│   │   ├── data_display_panel.dart
│   │   ├── main.dart
│   │   └── sensor_data.dart
│   ├── linux
│   │   ├── CMakeLists.txt
│   │   ├── flutter
│   │   └── runner
│   ├── macos
│   │   ├── Flutter
│   │   ├── Runner
│   │   ├── Runner.xcodeproj
│   │   ├── Runner.xcworkspace
│   │   └── RunnerTests
│   ├── pubspec.lock
│   ├── pubspec.yaml
│   ├── test
│   │   └── widget_test.dart
│   ├── web
│   │   ├── favicon.png
│   │   ├── icons
│   │   ├── index.html
│   │   └── manifest.json
│   └── windows
│       ├── CMakeLists.txt
│       ├── flutter
│       └── runner
└── requirements.txt

45 directories, 43 files
```

-   Ver 1.0

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
