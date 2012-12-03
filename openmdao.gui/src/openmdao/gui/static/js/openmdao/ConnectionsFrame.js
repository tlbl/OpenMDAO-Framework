
var openmdao = (typeof openmdao === "undefined" || !openmdao ) ? {} : openmdao ;

if (!Raphael.fn.hasOwnProperty('variableNode')) {
    Raphael.fn.variableNode = function(x, y, name) {
        this.x = x;
        this.y = y;
        this.name = name;
        this.rectObj = paper.rect(x, y, 125, 30, 10, 10, {'stroke':'#0b93d5', 'fill':'#999999', "stroke-width": 2});
        this.textObj = paper.text(this.x, this.y, this.name);
        this.entireSet = paper.set(this.rectObj, this.textObj);
        return this
    }
}

openmdao.ConnectionsFrame = function(model,pathname,src_comp,dst_comp) {
    var id = ('ConnectionsFrame-'+pathname).replace(/\./g,'-');
    openmdao.ConnectionsFrame.prototype.init.call(this, id,
        'Connections: '+openmdao.Util.getName(pathname));

    /***********************************************************************
     *  private
     ***********************************************************************/

    // initialize private variables
    var self = this,
        // component selectors
        componentsHTML = '<div style="width:100%;background:grey"><table>'
                       +        '<tr><td>Source Component:</td>'
                       +            '<td>Target Component:</td>'
                       +        '</tr>'
                       +        '<tr><td><input id="src_cmp_list" /></td>'
                       +            '<td><input id="dst_cmp_list" /></td>'
                       +        '</tr>'
                       + '</table></div>',
        componentsDiv = jQuery(componentsHTML)
            .appendTo(self.elm),
        src_cmp_selector = componentsDiv.find('#src_cmp_list'),
        dst_cmp_selector = componentsDiv.find('#dst_cmp_list'),
        component_list = [],
        // connections diagram
        connectionsCSS = 'background:grey; position:relative; width:100%; overflow-x:hidden; overflow-y:auto; min-height:300px;',
        connectionsDiv = jQuery('<div id="'+id+'-connections" style="'+connectionsCSS+'">')
            .appendTo(self.elm)
            .svg(),
        // variable selectors and connect button
        variablesCSS = 'background:grey; position:relative; width:100%;',
        variablesHTML = '<div style="'+variablesCSS+'"><table>'
                      +        '<tr><td>Source Variable:</td>'
                      +        '    <td>Target Variable:</td>'
                      +        '</tr>'
                      +        '<tr><td><input  id="src_var_list" /></td>'
                      +        '    <td><input  id="dst_var_list" /></td>'
                      +        '    <td><button id="connect" class="button">Connect</button></td>'
                      +        '</tr>'
                      + '</table></div>',
        variablesDiv = jQuery(variablesHTML)
            .appendTo(self.elm),
        src_var_selector = variablesDiv.find('#src_var_list'),
        dst_var_selector = variablesDiv.find('#dst_var_list'),
        connect_button = variablesDiv.find('#connect')
                        .click(function() {
                            var src = src_var_selector.val();
                            var dst = dst_var_selector.val();
                            model.issueCommand(self.pathname+'.connect("'+src+'","'+dst+'")');
                            src_var_selector.val('');
                            dst_var_selector.val('');
                        }),
        assemblyKey = '<Assembly>',
        assemblyCSS = {'font-style':'italic', 'opacity':'0.5'},
        normalCSS = {'font-style':'normal', 'opacity':'1.0'},
        showAllVariables = false,  // only show connected variables by default
        contextMenu = jQuery("<ul class='context-menu'>")
            .appendTo(connectionsDiv),
        r = connectionsDiv.svg('get'),
        rectCSS = {'stroke-width':2, 'stroke':'#0b93d5', 'fill':'#999999'},
        textCSS = {'stroke':'#000000', 'text-anchor':'middle'};
//        r = Raphael(connectionsDiv.attr('id'));

debug.info('r',r);

    self.pathname = null;

    // create context menu for toggling the showAllVariables option
    contextMenu.uniqueId();
    contextMenu.append(jQuery('<li>Toggle All Variables</li>').click(function(e) {
        if (showAllVariables) {
            showAllVariables = false;
            showConnections();
        }
        else {
            showAllVariables = true;
            showConnections();
        }
    }));
    ContextMenu.set(contextMenu.attr('id'), connectionsDiv.attr('id'));

    function setupSelector(selector) {
        // if selector gains focus with assemblyKey then clear it
        selector.focus(function() {
            selector = jQuery(this);
            if (selector.val() === assemblyKey) {
                selector.val('').css(normalCSS);
            }
        });

        // process new selector value when selector loses focus
        selector.bind('blur', function(e) {

            selector.autocomplete('close');

            if (e.target.value === '' || e.target.value === assemblyKey) {
                selector.val(assemblyKey);
                selector.css(assemblyCSS);
            }

            if (selector.attr('id') === src_cmp_selector.attr('id')) {
                if (e.target.value === assemblyKey) {
                    self.src_comp = '';
                }
                else {
                    if (jQuery.inArray(e.target.value, component_list) >= 0) {
                        self.src_comp = e.target.value;
                    }
                    else {
                        selector.val(self.src_comp);
                    }
                }
            }
            else {
                if (e.target.value === assemblyKey) {
                    self.dst_comp = '';
                }
                else {
                    if (jQuery.inArray(e.target.value, component_list) >= 0) {
                        self.dst_comp = e.target.value;
                    }
                    else {
                        selector.val(self.dst_comp);
                    }
                }
            }

            if (e.target.value === '' || e.target.value === assemblyKey) {
                selector.val(assemblyKey);
                selector.css(assemblyCSS);
            }

            showConnections();
        });

        // set autocomplete to trigger blur (remove focus)
        selector.autocomplete({
            select: function(event, ui) {
                if (ui.item.value === '') {
                    selector.val(assemblyKey);
                    selector.css(assemblyCSS);
                }
                else {
                    selector.val(ui.item.value);
                    selector.css(normalCSS);
                }
                selector.blur();
            },
            delay: 0,
            minLength: 0
        });

        // set enter key to trigger blur (remove focus)
        selector.bind('keypress.enterkey', function(e) {
            if (e.which === 13) {
                selector.blur();
            }
        });
    }

    setupSelector(src_cmp_selector);
    setupSelector(dst_cmp_selector);

    function loadData(data) {
        if (!data || !data.Dataflow || !data.Dataflow.components
                  || !data.Dataflow.components.length) {
            // don't have what we need, probably something got deleted
            debug.warn('ConnectionFrame.loadData(): Invalid data',data);
            self.close();
        }
        else {
            component_list = jQuery.map(data.Dataflow.components,
                                   function(comp,idx){ return comp.name; });
            component_list.push(assemblyKey);

            // update the output & input selectors with component list
            src_cmp_selector.html('');
            src_cmp_selector.autocomplete({source: component_list});

            dst_cmp_selector.html('');
            dst_cmp_selector.autocomplete({source: component_list});
        }

        if (self.src_comp) {
            src_cmp_selector.val(self.src_comp);
            src_cmp_selector.css(normalCSS);
        }
        else {
            src_cmp_selector.val(assemblyKey);
            src_cmp_selector.css(assemblyCSS);
        }
        if (self.dst_comp) {
            dst_cmp_selector.val(self.dst_comp);
            dst_cmp_selector.css(normalCSS);
        }
        else {
            dst_cmp_selector.val(assemblyKey);
            dst_cmp_selector.css(assemblyCSS);
        }
        showConnections();
    }

    function loadConnectionData(data) {
        debug.info('ConnectionFrame.loadConnectionData(): data',data);
        if (!data || !data.sources || !data.destinations) {
            // don't have what we need, probably something got deleted
            debug.warn('ConnectionFrame.loadConnectionData(): Invalid data',data);
            self.close();
        }
        else {
//            connectionsDiv.html('');
            r.clear();
            figures = {};
            var i = 0,
                x = 5,
                y = 10,
                conn_list = jQuery.map(data.connections, function(n) {
                    return n;
                }),
                src_list  = jQuery.map(data.sources, function(n) {
                    return self.src_comp ? self.src_comp+'.'+n.name : n.name;
                }),
                dst_list   = jQuery.map(data.destinations, function(n) {
                    return self.dst_comp ? self.dst_comp+'.'+n.name : n.name;
                });

            for (i = 0; i <conn_list.length; i++) {
                if (conn_list[i].indexOf('.') >= 0) {
                    conn_list[i]=conn_list[i].split('.')[1];
                }
            }


            jQuery.each(data.sources, function(idx,srcvar) {
                if (showAllVariables || conn_list.contains(srcvar.name)) {
                    var src_name = self.src_comp ? self.src_comp+'.'+srcvar.name : srcvar.name,
                        src_path = self.pathname+'.'+src_name,
                        fig = new openmdao.VariableFigure(model,src_path,srcvar,'output');
                    fig = r.rect(x, y, 125, 30, 10, 10, {'stroke':'#0b93d5', 'fill':'#999999', "stroke-width": 2});
                    r.text(fig,src_name);
//                    fig.attr('title',src_name);
//                    connectionsDiv.find('a[title="'+src_name+'"]').find('rect').append('<text>'+src_name+'</text>');
//                    fig.attr({'stroke':'#0b93d5', 'fill':'#999999', "stroke-width": 2});
//                    connectionsDiv.append(fig.getElement());
//                    fig.setPosition(x,y);
//                    debug.info('ConnectionFrame.loadConnectionData(): srcvar', src_name, fig, x, y);
                    figures[src_name] = fig;
//                    y = y + fig.getHeight() + 10;
                    y = y + 50 + 10;
                }
            });
            var end_outputs = y;

            x = 200;
            y = 10;
            jQuery.each(data.destinations, function(idx,dstvar) {
                if (showAllVariables || conn_list.contains(dstvar.name)) {
                    var dst_name = self.dst_comp ? self.dst_comp+'.'+dstvar.name : dstvar.name,
                        dst_path = self.pathname+'.'+dst_name,
                        fig = new openmdao.VariableFigure(model,dst_path,dstvar,'input');
                    fig = r.rect(x, y, 125, 30, 10, 10, {'stroke':'#0b93d5', 'fill':'#999999', "stroke-width": 2});
                    r.text(fig,dst_name);
//                    fig.attr('title',dst_name);
//                    connectionsDiv.find('a[title="'+dst_name+'"]').find('rect').append('<text>'+dst_name+'</text>');
//                    fig.attr({'stroke':'#0b93d5', 'fill':'#999999', "stroke-width": 2});
//                    connectionsDiv.append(fig.getElement());
//                    fig.setPosition(x,y);
//                    debug.info('ConnectionFrame.loadConnectionData(): dstvar', dst_name, fig, x, y);
                    figures[dst_name] = fig;
//                    y = y + fig.getHeight() + 10;
                    y = y + 50 + 10;
                }
            });
            var end_inputs = y;

            var height = Math.max(end_inputs, end_outputs, 25); // + 'px';
//            connectionsDiv.height(height);
//            r.setSize(connectionsDiv.width(), height);

            connectionsDiv.show();
            variablesDiv.show();

            jQuery.each(data.connections,function(idx,conn) {
                var src_name = conn[0],
                    dst_name = conn[1],
                    src_fig = figures[src_name],
                    dst_fig = figures[dst_name];
//                    src_port = src_fig.getPort("output"),
//                    dst_port = dst_fig.getPort("input");
//                c = new draw2d.Connection();
//                c.setSource(src_port);
//                c.setTarget(dst_port);
//                c.setTargetDecorator(new draw2d.ArrowConnectionDecorator());
//                c.setRouter(new draw2d.BezierConnectionRouter());
//                c.setCoronaWidth(10);
//                c.getContextMenu=function(){
//                    var menu=new draw2d.Menu();
//                    var oThis=this;
//                    menu.appendMenuItem(new draw2d.MenuItem("Disconnect",null,function(){
//                            var asm = self.pathname,
//                                cmd = asm + '.disconnect("'+src_name+'","'+dst_name+'")';
//                            model.issueCommand(cmd);
//                        })
//                    );
//                    return menu;
//                };
//                connectionsDiv.append(c);
//                src_port.setBackgroundColor(new draw2d.Color(0,0,0));
//                dst_port.setBackgroundColor(new draw2d.Color(0,0,0));
                r.connection(src_fig, dst_fig, "#000", "#fff");
            });

            // update the output & input selectors to current outputs & inputs
            src_var_selector.html('');
            src_var_selector.autocomplete({ source: src_list ,minLength:0});

            dst_var_selector.html('');
            dst_var_selector.autocomplete({ source: dst_list ,minLength:0});
        }
    }

    /** edit connections between the source and destination objects in the assembly */
    function showConnections() {
        if (self.src_comp !== null && self.dst_comp !== null) {
            model.getConnections(self.pathname, self.src_comp, self.dst_comp,
                loadConnectionData,
                function(jqXHR, textStatus, errorThrown) {
                    debug.error(jqXHR,textStatus,errorThrown);
                    self.close();
                }
            );
        }
        else {
            connectionsDiv.hide();
            variablesDiv.hide();
        }
    }

    /** handle message about the assembly */
    function handleMessage(message) {
        if (message.length !== 2 || message[0] !== self.pathname) {
            debug.warn('Invalid component data for:',self.pathname,message);
            debug.warn('message length',message.length,'topic',message[0]);
        }
        else {
            loadData(message[1]);
        }
    }

    /***********************************************************************
     *  privileged
     ***********************************************************************/

    /** if there is an object loaded, update it from the model */
    this.update = function() {
        if (self.pathname && self.pathname.length > 0) {
            self.editAssembly(self.pathname,self.src_comp,self.dst_comp);
        }
    };

    /** get the specified assembly from model */
    this.editAssembly = function(path, src_comp, dst_comp) {
        if (self.pathname !== path) {
           if (self.pathname !== null) {
                model.removeListener(self.pathname, handleMessage);
            }
            self.pathname = path;
            model.addListener(self.pathname, handleMessage);
        }

        self.src_comp = src_comp;
        self.dst_comp = dst_comp;

        model.getComponent(path, loadData,
            function(jqXHR, textStatus, errorThrown) {
                debug.warn('ConnectionsFrame.editAssembly() Error:',
                            jqXHR, textStatus, errorThrown);
                // assume component has been deleted, so close frame
                self.close();
            }
        );
    };

    this.destructor = function() {
        if (self.pathname && self.pathname.length>0) {
            model.removeListener(self.pathname, handleMessage);
        }
    };

    this.editAssembly(pathname, src_comp, dst_comp);
};

/** set prototype */
openmdao.ConnectionsFrame.prototype = new openmdao.BaseFrame();
openmdao.ConnectionsFrame.prototype.constructor = openmdao.ConnectionsFrame;
