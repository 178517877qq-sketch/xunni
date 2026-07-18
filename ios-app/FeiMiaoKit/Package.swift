// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "FeiMiaoKit",
    platforms: [
        .iOS(.v18),
        .macOS(.v14),
    ],
    products: [
        .library(name: "FeiMiaoDomain", targets: ["FeiMiaoDomain"]),
        .library(name: "FeiMiaoData", targets: ["FeiMiaoData"]),
    ],
    dependencies: [
        .package(url: "https://github.com/groue/GRDB.swift.git", exact: "7.11.1"),
        .package(url: "https://github.com/weichsel/ZIPFoundation.git", exact: "0.9.20"),
    ],
    targets: [
        .target(name: "FeiMiaoDomain"),
        .target(
            name: "FeiMiaoData",
            dependencies: [
                "FeiMiaoDomain",
                .product(name: "GRDB", package: "GRDB.swift"),
                "ZIPFoundation",
            ]
        ),
        .testTarget(name: "FeiMiaoDomainTests", dependencies: ["FeiMiaoDomain"]),
        .testTarget(
            name: "FeiMiaoDataTests",
            dependencies: [
                "FeiMiaoData",
                "FeiMiaoDomain",
                .product(name: "GRDB", package: "GRDB.swift"),
                "ZIPFoundation",
            ]
        ),
    ],
    swiftLanguageModes: [.v5]
)
