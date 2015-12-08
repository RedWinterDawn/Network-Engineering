var w = 1200,
    h = 800,
    fill = d3.scale.category20();

var vis = d3.select("#chart")
  .append("svg:svg")
    .attr("width", w)
    .attr("height", h);

d3.json("force-single-dmvpn-failure.json", function(json) {
  var force = d3.layout.force()
      .charge(-500)
      .linkDistance(200)
      .nodes(json.nodes)
      .links(json.links)
      .size([w, h])
      .start();

  var link = vis.selectAll("line.link")
      .data(json.links)
    .enter().append("svg:path")
      .attr("class", "link")
      .style("stroke-width", function(d) { return d.penwidth; })
      .style("fill", "none")
      .style("stroke", function(d) { console.log(d.color); return d.color; })
      .style("stroke-dasharray", function(d){
                                    console.log(d.cls);
                                    if(d.cls == "DMVPN"){
                                      console.log("dmvpn matched");
                                      return "10,10";
                                    } else {
                                      return "none"; 
                                    }
                                  });

  var gnode = vis.selectAll("g.gnode")
      .data(json.nodes)
    .enter().append("g")
    .classed("gnode", true);

  var node = gnode.append("svg:circle")
      .attr("class", "node")
      .attr("r", 5)
      .style("fill", function(d) { return fill(d.group); })
      .call(force.drag);

  node.append("svg:title")
      .text(function(d) { return d.name; });

  gnode.append("svg:text")
      .attr("dx", ".5em")
      .attr("dy", ".5em")
      .text(function(d) {
          //console.log(d.attr.name);
          return d.attr.name;
      });

  vis.style("opacity", 1e-6)
    .transition()
      .duration(1000)
      .style("opacity", 1);

  // force.on("tick", function() {
  //   link.attr("x1", function(d) { return d.source.x; })
  //       .attr("y1", function(d) { return d.source.y; })
  //       .attr("x2", function(d) { return d.target.x; })
  //       .attr("y2", function(d) { return d.target.y; });

  //   gnode.attr("transform", function(d) { 
  //       return 'translate(' + [d.x, d.y] + ')'; 
  //   });
  //   // gnode.attr("cx", function(d) { return d.x; })
  //   //     .attr("cy", function(d) { return d.y; });
  // });
  //});
  force.on("tick", tick);

  function tick() {
      link.attr("d", function (d) {
          var x1 = d.source.x,
              y1 = d.source.y,
              x2 = d.target.x,
              y2 = d.target.y,
              dx = x2 - x1,
              dy = y2 - y1,
              dr = Math.sqrt(dx * dx + dy * dy) - Math.sqrt(300*(d.count-1));
              // Set dr to 0 for straight edges.
              // Set dr to Math.sqrt(dx * dx + dy * dy) for a simple curve.
              // Assuming a simple curve, decrease dr to space curves.
              // There's probably a better decay function that spaces things nice and evenly.
              if (d.count % 2){
                return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,1 " + x2 + "," + y2;
              }else{
                return "M" + x1 + "," + y1 + "A" + dr + "," + dr + " 0 0,0 " + x2 + "," + y2;
              }
      });

      gnode.attr("transform", function (d) {
          return "translate(" + [d.x,d.y] + ")";
      });
  }
});
