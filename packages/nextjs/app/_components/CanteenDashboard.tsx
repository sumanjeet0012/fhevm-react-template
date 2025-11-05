"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import { useFhevm } from "@fhevm-sdk";
import { useAccount } from "wagmi";
import { RainbowKitCustomConnectButton } from "~~/components/helper/RainbowKitCustomConnectButton";
import { useCanteenWagmi } from "~~/hooks/canteen-example/useCanteenWagmi";

/**
 * CanteenDashboard - Main component for the Canteen container orchestrator
 *
 * Features:
 * - Display registered operator nodes
 * - Add/Remove Docker images with replica counts
 * - Show deployed containers across the cluster
 * - Real-time updates from blockchain events
 */
export const CanteenDashboard = () => {
  const { isConnected, chain } = useAccount();
  const chainId = chain?.id;

  // Local state for forms
  const [addImageName, setAddImageName] = useState("");
  const [addImageReplicas, setAddImageReplicas] = useState("3");
  const [removeImageName, setRemoveImageName] = useState("");

  //////////////////////////////////////////////////////////////////////////////
  // FHEVM instance
  //////////////////////////////////////////////////////////////////////////////

  const provider = useMemo(() => {
    if (typeof window === "undefined") return undefined;
    return (window as any).ethereum;
  }, []);

  const initialMockChains = { 31337: "http://localhost:8545" };

  const { instance: fhevmInstance } = useFhevm({
    provider,
    chainId,
    initialMockChains,
    enabled: true,
  });

  //////////////////////////////////////////////////////////////////////////////
  // Canteen contract hook
  //////////////////////////////////////////////////////////////////////////////

  const canteen = useCanteenWagmi({
    instance: fhevmInstance,
    initialMockChains,
  });

  //////////////////////////////////////////////////////////////////////////////
  // UI Styling
  //////////////////////////////////////////////////////////////////////////////

  const buttonClass =
    "inline-flex items-center justify-center px-6 py-3 font-semibold shadow-lg " +
    "transition-all duration-200 hover:scale-105 " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 " +
    "disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed";

  const primaryButtonClass =
    buttonClass + " bg-[#FFD208] text-[#2D2D2D] hover:bg-[#A38025] focus-visible:ring-[#2D2D2D] cursor-pointer";

  const secondaryButtonClass =
    buttonClass + " bg-black text-[#F4F4F4] hover:bg-[#1F1F1F] focus-visible:ring-[#FFD208] cursor-pointer";

  const inputClass =
    "px-4 py-2 border-2 border-gray-300 rounded-md focus:border-[#FFD208] focus:outline-none " +
    "text-gray-900 bg-white";

  const cardClass = "bg-white shadow-xl border-2 border-gray-200 p-6 mb-6 text-gray-900";
  const titleClass = "font-bold text-gray-900 text-2xl mb-4 border-b-2 border-[#FFD208] pb-2";

  //////////////////////////////////////////////////////////////////////////////
  // Handlers
  //////////////////////////////////////////////////////////////////////////////

  const handleAddImage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addImageName || !addImageReplicas) return;

    await canteen.addImage(addImageName, parseInt(addImageReplicas, 10));
    setAddImageName("");
    setAddImageReplicas("3");
  };

  const handleRemoveImage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!removeImageName) return;

    await canteen.removeImage(removeImageName);
    setRemoveImageName("");
  };

  //////////////////////////////////////////////////////////////////////////////
  // UI Rendering
  //////////////////////////////////////////////////////////////////////////////

  if (!isConnected) {
    return (
      <div className="max-w-7xl mx-auto p-6 text-gray-900">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white shadow-2xl p-12 mb-8 border-2 border-gray-700 rounded-lg">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-bold mb-4">
              <span className="text-[#FFD208]">Veil Stack</span>
            </h1>
            <p className="text-2xl text-gray-300 mb-6">Confidential Decentralized Container Orchestration</p>
            <div className="flex justify-center">
              <RainbowKitCustomConnectButton />
            </div>
          </div>
        </div>

        {/* Project Overview */}
        <div className="bg-white shadow-xl p-8 mb-8 border-2 border-gray-200 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-gray-900 border-b-4 border-[#FFD208] pb-3">
            What is Veil Stack?
          </h2>
          <p className="text-lg text-gray-700 leading-relaxed mb-4">
            Veil Stack is a <strong>confidential, decentralized container orchestration platform</strong> designed to
            enable distributed compute environments to schedule and manage workloads without exposing infrastructure
            telemetry or operational metadata.
          </p>
        </div>

        {/* Key Technology */}
        <div className="bg-white shadow-xl p-8 mb-8 border-2 border-gray-200 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-gray-900 border-b-4 border-[#FFD208] pb-3">
            Built on Zama FHE Technology
          </h2>
          <p className="text-lg text-gray-700 leading-relaxed mb-4">
            Built on <strong>Zama&apos;s Universal Fully Homomorphic Encryption (FHE) SDK</strong>, Veil Stack performs
            scheduling and policy logic directly over encrypted node metrics, ensuring complete confidentiality even in
            untrusted or multi-organization clusters.
          </p>
          <div className="bg-blue-50 border-l-4 border-blue-500 p-6 mt-6">
            <p className="text-gray-800 leading-relaxed">
              <strong>Unlike traditional orchestrators</strong> such as Kubernetes or Nomad, which require full
              visibility into every node&apos;s CPU, memory, and workload profiles,{" "}
              <strong>Veil Stack removes that requirement entirely</strong>. Each node encrypts its telemetry using
              Zama FHE, allowing scheduling decisions and policy enforcement to occur without ever decrypting the data.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="bg-white shadow-xl p-8 mb-8 border-2 border-gray-200 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-gray-900 border-b-4 border-[#FFD208] pb-3">How It Works</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                <span className="text-3xl mr-3">🔐</span>
                Encrypted Resource Metrics
              </h3>
              <p className="text-gray-700 leading-relaxed">
                CPU, memory, and system load are securely shared across the cluster while maintaining privacy through
                homomorphic encryption.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                <span className="text-3xl mr-3">🧮</span>
                Computation Over Ciphertext
              </h3>
              <p className="text-gray-700 leading-relaxed">
                Scheduling algorithms, including cost functions, replica placement, and priority rules, run entirely
                over ciphertext without decryption.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                <span className="text-3xl mr-3">📋</span>
                Private Policy Evaluation
              </h3>
              <p className="text-gray-700 leading-relaxed">
                Policies like quotas and placement constraints are evaluated privately to preserve operational secrecy
                across organizations.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                <span className="text-3xl mr-3">🤝</span>
                Trustless Coordination
              </h3>
              <p className="text-gray-700 leading-relaxed">
                Enables coordination across institutions without the need for trust agreements, NDAs, or data exposure.
              </p>
            </div>
          </div>
        </div>

        {/* Use Cases */}
        <div className="bg-white shadow-xl p-8 mb-8 border-2 border-gray-200 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-gray-900 border-b-4 border-[#FFD208] pb-3">
            Real-World Use Cases
          </h2>
          <div className="space-y-4">
            <div className="flex items-start">
              <span className="text-2xl mr-4">🏥</span>
              <div>
                <h4 className="font-bold text-lg text-gray-900">Multi-Hospital ML Networks</h4>
                <p className="text-gray-700">
                  Deploy orchestration in sensitive healthcare environments without exposing patient data or
                  infrastructure details.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="text-2xl mr-4">☁️</span>
              <div>
                <h4 className="font-bold text-lg text-gray-900">Cross-Cloud Scientific Compute Alliances</h4>
                <p className="text-gray-700">
                  Enable collaborative research computing across different cloud providers while maintaining data
                  privacy.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="text-2xl mr-4">🎮</span>
              <div>
                <h4 className="font-bold text-lg text-gray-900">Decentralized GPU Networks</h4>
                <p className="text-gray-700">
                  Coordinate GPU resources across distributed networks without revealing computational workload details.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="text-2xl mr-4">🛡️</span>
              <div>
                <h4 className="font-bold text-lg text-gray-900">Government & Defense Infrastructure</h4>
                <p className="text-gray-700">
                  Deploy secure orchestration in high-security environments with complete operational confidentiality.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Screenshots */}
        <div className="bg-white shadow-xl p-8 mb-8 border-2 border-gray-200 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-gray-900 border-b-4 border-[#FFD208] pb-3">
            Platform Screenshots
          </h2>
          <div className="space-y-8">
            <div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Cluster Visualization Dashboard</h3>
              <Image
                src="/screenshot-dashboard.png"
                alt="Veil Stack Cluster Dashboard"
                width={1200}
                height={800}
                className="w-full rounded-lg border-2 border-gray-300 shadow-md"
              />
              <p className="text-gray-600 mt-2 text-sm italic">
                Visual representation of the decentralized container orchestrator showing deployed nodes and their
                connections.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Node Registration & Event Logs</h3>
              <Image
                src="/screenshot-events.png"
                alt="Node Registration Events"
                width={1200}
                height={800}
                className="w-full rounded-lg border-2 border-gray-300 shadow-md"
              />
              <p className="text-gray-600 mt-2 text-sm italic">
                Blockchain event logs showing node registrations and image updates, demonstrating transparent operations
                while maintaining data privacy.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">P2P Node Startup & Configuration</h3>
              <Image
                src="/screenshot-node.png"
                alt="Node Startup Configuration"
                width={1200}
                height={800}
                className="w-full rounded-lg border-2 border-gray-300 shadow-md"
              />
              <p className="text-gray-600 mt-2 text-sm italic">
                Node initialization showing Hyperswarm P2P networking, cluster health monitoring, and container
                deployment status.
              </p>
            </div>
          </div>
        </div>

        {/* Conclusion */}
        <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white shadow-xl p-8 mb-8 border-2 border-gray-700 rounded-lg">
          <h2 className="text-3xl font-bold mb-6 text-white border-b-4 border-[#FFD208] pb-3">
            The Future of Orchestration
          </h2>
          <p className="text-lg text-gray-200 leading-relaxed mb-6">
            In essence,{" "}
            <strong className="text-[#FFD208]">
              Veil Stack redefines container orchestration through cryptographic privacy
            </strong>
            , bringing a new era of confidential orchestration where intelligent scheduling decisions can be made
            securely and transparently—without revealing any underlying operational data.
          </p>
          <div className="flex justify-center">
            <RainbowKitCustomConnectButton />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 text-gray-900">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">
          <span className="text-[#FFD208]">canteen.</span>
        </h1>
        <p className="text-gray-600 text-lg">A decentralized container orchestrator powered by FHE</p>
      </div>

      {/* Status Card */}
      <div className={cardClass}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500">Contract Address</p>
            <p className="font-mono text-sm break-all">{canteen.contractAddress || "N/A"}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Active Operator Nodes</p>
            <p className="text-2xl font-bold text-[#FFD208]">{canteen.membersCount}</p>
            <p className="text-xs text-gray-400 mt-1">
              {canteen.membersCount === 0 ? "No active nodes" : `${canteen.membersCount} node(s) online`}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Deployed Images</p>
            <p className="text-2xl font-bold text-[#FFD208]">{canteen.imagesCount}</p>
          </div>
        </div>
      </div>

      {/* Message Display */}
      {canteen.message && (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
          <p className="text-blue-700">{canteen.message}</p>
        </div>
      )}

      {/* Add Image Form */}
      <div className={cardClass}>
        <h2 className={titleClass}>Deploy Container Image</h2>
        <form onSubmit={handleAddImage} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Image Name</label>
              <input
                type="text"
                className={inputClass}
                placeholder="e.g., nginx, redis, mongo"
                value={addImageName}
                onChange={e => setAddImageName(e.target.value)}
                disabled={canteen.isProcessing}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Number of Replicas</label>
              <input
                type="number"
                className={inputClass}
                placeholder="3"
                min="1"
                max="10"
                value={addImageReplicas}
                onChange={e => setAddImageReplicas(e.target.value)}
                disabled={canteen.isProcessing}
              />
            </div>
          </div>
          <button
            type="submit"
            className={primaryButtonClass}
            disabled={canteen.isProcessing || !addImageName || !addImageReplicas}
          >
            {canteen.isProcessing ? "Processing..." : "Deploy Image"}
          </button>
        </form>
      </div>

      {/* Remove Image Form */}
      <div className={cardClass}>
        <h2 className={titleClass}>Remove Container Image</h2>
        <form onSubmit={handleRemoveImage} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Image Name</label>
            <input
              type="text"
              className={inputClass}
              placeholder="e.g., nginx"
              value={removeImageName}
              onChange={e => setRemoveImageName(e.target.value)}
              disabled={canteen.isProcessing}
            />
          </div>
          <button type="submit" className={secondaryButtonClass} disabled={canteen.isProcessing || !removeImageName}>
            {canteen.isProcessing ? "Processing..." : "Remove Image"}
          </button>
        </form>
      </div>

      {/* Deployed Images List */}
      <div className={cardClass}>
        <h2 className={titleClass}>Active Deployments</h2>
        {canteen.images.length === 0 ? (
          <p className="text-gray-500 italic">No images deployed yet. Deploy your first container above!</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {canteen.images.map((image: any, index) => (
              <div
                key={index}
                className="bg-gray-50 border-2 border-gray-200 p-4 rounded-md hover:border-[#FFD208] transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-2xl">🐳</span>
                  <span className="font-semibold">{image.name || image}</span>
                </div>
                {image.replicas !== undefined ? (
                  <div className="mt-2">
                    <p className="text-sm text-gray-600">
                      Replicas:{" "}
                      <span className="font-bold text-green-600">
                        {image.deployed}/{image.replicas}
                      </span>
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{image.active ? "✅ Active" : "⚠️ Inactive"}</p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 mt-2">Active deployment</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Operator Nodes Info */}
      <div className={cardClass}>
        <h2 className={titleClass}>Active Operator Nodes</h2>
        <p className="text-gray-600 mb-4">
          {canteen.membersCount > 0
            ? `${canteen.membersCount} active operator node(s) online and ready to deploy containers.`
            : "No active operator nodes. Start Python operators to register nodes."}
        </p>
        {canteen.membersCount > 0 && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4">
            <p className="text-green-700">
              ✅ {canteen.membersCount} operator node(s) actively monitoring the blockchain for deployment requests.
            </p>
          </div>
        )}
        {canteen.membersCount === 0 && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <p className="text-yellow-700 mb-2">⚠️ To register operator nodes, run the Python backend:</p>
            <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
              {`python python/main.py --memory 2000 --port 5000`}
            </pre>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border-2 border-blue-200 p-6 mt-6">
        <h3 className="font-bold text-blue-900 mb-3">🚀 How It Works</h3>
        <ol className="list-decimal list-inside space-y-2 text-blue-800">
          <li>Start Python operator nodes (they register with the smart contract)</li>
          <li>Deploy a container image using the form above</li>
          <li>The smart contract finds the best nodes using FHE-encrypted memory values</li>
          <li>Operators pull and start Docker containers automatically</li>
          <li>View active deployments in real-time on this dashboard</li>
        </ol>
      </div>
    </div>
  );
};
