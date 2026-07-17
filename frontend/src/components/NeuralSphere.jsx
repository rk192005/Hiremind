import React, { useMemo, useRef, useEffect } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';

const AGENT_CLUSTERS = [
  { id: 'cluster_intake', name: 'intake', color: '#7C3AED', position: { x: -30, y: 30, z: 10 } },
  { id: 'cluster_retrieval', name: 'retrieval', color: '#7C3AED', position: { x: 30, y: 30, z: -10 } },
  { id: 'cluster_scoring', name: 'scoring', color: '#22D3EE', position: { x: 40, y: -10, z: 20 } },
  { id: 'cluster_interview_prep', name: 'interview_prep', color: '#4B5563', position: { x: 0, y: -40, z: 0 } },
  { id: 'cluster_bias_audit', name: 'bias_audit', color: '#4B5563', position: { x: -40, y: -10, z: -20 } },
];

export default function NeuralSphere({ viewState = 'landing', agentStatuses = {} }) {
  const fgRef = useRef();

  // Generate graph data once
  const graphData = useMemo(() => {
    const nodes = [];
    const links = [];

    // 1. Create main agent clusters
    AGENT_CLUSTERS.forEach((cluster, i) => {
      // Main cluster node
      nodes.push({
        id: cluster.id,
        group: 'agent',
        agentName: cluster.name,
        val: 10,
        fx: cluster.position.x,
        fy: cluster.position.y,
        fz: cluster.position.z,
      });

      // Create satellite nodes around the cluster
      for (let j = 0; j < 6; j++) {
        const satId = `${cluster.id}_sat_${j}`;
        nodes.push({
          id: satId,
          group: 'satellite',
          parentAgent: cluster.name,
          val: 3,
        });
        links.push({ source: cluster.id, target: satId });
      }

      // Connect to the next cluster to form a pentagon logic
      const nextCluster = AGENT_CLUSTERS[(i + 1) % AGENT_CLUSTERS.length];
      links.push({ source: cluster.id, target: nextCluster.id, isAgentLink: true });
    });

    // 2. Add random background nodes to form a sphere
    const numBgNodes = 150;
    const radius = 60;
    for (let i = 0; i < numBgNodes; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);

      const bgNodeId = `bg_${i}`;
      nodes.push({
        id: bgNodeId,
        group: 'background',
        val: 1,
        fx: x,
        fy: y,
        fz: z,
      });

      // Randomly connect some background nodes
      if (i > 0 && Math.random() > 0.5) {
        links.push({ source: bgNodeId, target: `bg_${Math.floor(Math.random() * i)}` });
      }
    }

    return { nodes, links };
  }, []);

  // Update camera based on viewState
  useEffect(() => {
    if (!fgRef.current) return;
    const controls = fgRef.current.controls();
    if (controls) {
      controls.enableZoom = false;
      controls.enablePan = false;
      controls.autoRotate = true;
      controls.autoRotateSpeed = viewState === 'processing' ? 2.0 : 0.5;
    }
  }, [viewState]);

  // Determine node color based on agent status
  const getNodeColor = (node) => {
    let agentName = null;
    if (node.group === 'agent') agentName = node.agentName;
    if (node.group === 'satellite') agentName = node.parentAgent;

    if (agentName) {
      const status = agentStatuses[agentName];
      if (status === 'completed') return '#7C3AED'; // Violet
      if (status === 'running') return '#22D3EE'; // Cyan
      if (status === 'error') return '#f87171'; // Red
      
      // In landing state, everything is glowing violet/cyan mix.
      // In processing, waiting ones are dim.
      if (viewState === 'processing') return '#334155'; // Dim gray for waiting
      return node.id.length % 2 === 0 ? '#7C3AED' : '#22D3EE';
    }

    // Background nodes
    return 'rgba(124, 58, 237, 0.4)';
  };

  // Node resolution/size
  const getNodeRelSize = (node) => {
    if (node.group === 'agent') {
      return agentStatuses[node.agentName] === 'running' ? 8 : 6;
    }
    return node.val || 2;
  };

  return (
    <div className={`transition-all duration-1000 ease-in-out absolute z-0
      ${viewState === 'results' 
        ? 'w-[150px] h-[150px] top-4 left-4' // Top-left miniaturized
        : 'w-full h-full inset-0 flex items-center justify-center' // Centered
      }
    `}>
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={viewState === 'results' ? 150 : (window.innerWidth || 1000)}
        height={viewState === 'results' ? 150 : (window.innerHeight || 800)}
        nodeColor={getNodeColor}
        nodeRelSize={2}
        nodeVal={getNodeRelSize}
        nodeResolution={16}
        linkOpacity={0.2}
        linkColor={() => 'rgba(124, 58, 237, 0.3)'}
        linkDirectionalParticles={(link) => {
          if (link.isAgentLink && viewState === 'processing') {
            return 2; // Show particles on agent links during processing
          }
          return 0;
        }}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => '#22D3EE'}
        backgroundColor="rgba(0,0,0,0)" // Transparent so our CSS mesh background shows
        showNavInfo={false}
      />
    </div>
  );
}
